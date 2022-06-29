from mlflow_export_import.model.export_model import ModelExporter
from mlflow_export_import.model.import_model import ModelImporter
from mlflow_export_import import utils
import utils_test
import compare_utils
from init_tests import mlflow_context

def test_export_import_model(mlflow_context):
    run_src = _create_run(mlflow_context.client_src)
    exporter = ModelExporter(mlflow_context.client_src)
    model_name_src = utils_test.mk_test_object_name_default()
    model_src = mlflow_context.client_src.create_registered_model(model_name_src)
    source = f"{run_src.info.artifact_uri}/model"
    mlflow_context.client_src.create_model_version(model_name_src, source, run_src.info.run_id)
    exporter.export_model(model_name_src, mlflow_context.output_dir)

    model_name_dst = utils_test.create_dst_model_name(model_name_src)
    experiment_name =  model_name_dst
    importer = ModelImporter( mlflow_context.client_dst)
    importer.import_model(model_name_dst, mlflow_context.output_dir, experiment_name, delete_model=True, verbose=False, sleep_time=10)
    model_dst = mlflow_context.client_dst.get_registered_model(model_name_dst)

    model_src = mlflow_context.client_src.get_registered_model(model_name_src)
    assert len(model_src.latest_versions) == len(model_dst.latest_versions)

    _compare_models(model_src, model_dst)
    _compare_version_lists(mlflow_context, mlflow_context.output_dir, model_src.latest_versions, model_dst.latest_versions)

def test_export_import_model_stages(mlflow_context):
    exporter = ModelExporter(mlflow_context.client_src, stages=["Production","Staging"])
    model_name_src = utils_test.mk_test_object_name_default()
    model_src = mlflow_context.client_src.create_registered_model(model_name_src)

    _create_version(mlflow_context.client_src, model_name_src, "Production")
    _create_version(mlflow_context.client_src, model_name_src)
    vr_staging_src = _create_version(mlflow_context.client_src, model_name_src, "Staging")
    vr_prod_src = _create_version(mlflow_context.client_src, model_name_src, "Production")
    _create_version(mlflow_context.client_src, model_name_src, "Archived")
    exporter.export_model(model_name_src, mlflow_context.output_dir)

    model_name_dst = utils_test.create_dst_model_name(model_name_src)
    experiment_name =  model_name_dst
    importer = ModelImporter(mlflow_context.client_dst)
    importer.import_model(model_name_dst, mlflow_context.output_dir, experiment_name, delete_model=True, verbose=False, sleep_time=10)
    model_dst = mlflow_context.client_dst.get_registered_model(model_name_dst)

    model_dst = mlflow_context.client_dst.get_registered_model(model_name_dst)
    assert len(model_dst.latest_versions) == 2

    versions = mlflow_context.client_dst.get_latest_versions(model_name_dst)
    vr_prod_dst = [vr for vr in versions if vr.current_stage == "Production"][0]
    vr_staging_dst = [vr for vr in versions if vr.current_stage == "Staging"][0]

    _compare_models(model_src, model_dst)
    _compare_version_lists(
        mlflow_context, mlflow_context.output_dir,
        [vr_prod_src, vr_staging_src],
        [vr_prod_dst, vr_staging_dst])

def test_export_import_model_versions(mlflow_context):
    model_name_src = utils_test.mk_test_object_name_default()
    model_src = mlflow_context.client_src.create_registered_model(model_name_src)

    vr_staging_src = _create_version(mlflow_context.client_src, model_name_src, "Staging")
    vr_prod_src = _create_version(mlflow_context.client_src, model_name_src, "Production")

    exporter = ModelExporter(mlflow_context.client_src, versions=[vr_staging_src.version, vr_prod_src.version])
    exporter.export_model(model_name_src, mlflow_context.output_dir)

    model_name_dst = utils_test.create_dst_model_name(model_name_src)
    experiment_name = model_name_dst
    importer = ModelImporter(mlflow_context.client_dst)
    importer.import_model(model_name_dst, mlflow_context.output_dir, experiment_name, delete_model=True, verbose=False, sleep_time=10)

    model_dst = mlflow_context.client_dst.get_registered_model(model_name_dst)
    assert len(model_dst.latest_versions) == 2

    versions = mlflow_context.client_dst.get_latest_versions(model_name_dst)
    vr_prod_dst = [vr for vr in versions if vr.version == vr_prod_src.version][0]
    vr_staging_dst = [vr for vr in versions if vr.version == vr_staging_src.version][0]

    _compare_models(model_src, model_dst)
    _compare_version_lists(
        mlflow_context, mlflow_context.output_dir,
        [vr_prod_src, vr_staging_src],
        [vr_prod_dst, vr_staging_dst])


def _create_version(client, model_name, stage=None):
    run = _create_run(client)
    source = f"{run.info.artifact_uri}/model"
    vr = client.create_model_version(model_name, source, run.info.run_id)
    if stage:
        vr = client.transition_model_version_stage(model_name, vr.version, stage)
    return vr

def _create_run(client):
    _, run = utils_test.create_simple_run(client)
    return client.get_run(run.info.run_id)

def _compare_models(model_src, model_dst):
    assert model_src.description == model_dst.description
    assert model_src.tags == model_dst.tags

def _compare_version_lists(mlflow_context, output_dir, versions_src, versions_dst):
    for (vr_src, vr_dst) in zip(versions_src, versions_dst):
        _compare_versions(mlflow_context, output_dir, vr_src, vr_dst)

def _compare_versions(mlflow_context, output_dir, vr_src, vr_dst):
    assert vr_src.current_stage == vr_dst.current_stage
    assert vr_src.description == vr_dst.description
    assert vr_src.name == vr_dst.name
    assert vr_src.status == vr_dst.status
    assert vr_src.status_message == vr_dst.status_message
    if not utils.importing_into_databricks():
        assert vr_src.user_id == vr_dst.user_id
    assert vr_src.run_id != vr_dst.run_id
    run_src = mlflow_context.client_src.get_run(vr_src.run_id)
    run_dst = mlflow_context.client_dst.get_run(vr_dst.run_id)
    compare_utils.compare_runs(mlflow_context.client_src, mlflow_context.client_dst, output_dir, run_src, run_dst)


from mlflow_export_import.model.import_model import _extract_model_path

run_id = "48cf29167ddb4e098da780f0959fb4cf"
model_path = "models:/my_model"

def test_extract_model_path_databricks(mlflow_context):
    source = f"dbfs:/databricks/mlflow-tracking/4072937019901104/{run_id}/artifacts/{model_path}"
    _run_test_extract_model_path(source)

def test_extract_model_path_oss(mlflow_context):
    source = f"/opt/mlflow_context/local_mlrun/mlruns/3/{run_id}/artifacts/{model_path}"
    _run_test_extract_model_path(source)

def _run_test_extract_model_path(source):
    model_path2 = _extract_model_path(source, run_id)
    assert model_path == model_path2
