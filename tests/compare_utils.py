"""
Compare run utilities.
"""

import utils_test
from  mlflow_export_import import utils 


def compare_runs_with_source_tags(client_src, client_dst, run1, run2, output_dir):
    exp = client_src.get_experiment(run1.info.experiment_id)

    source_tags2 = { k:v for k,v in run2.data.tags.items() if k.startswith("mlflow_export_import.") }
    assert exp.name == source_tags2[f"{utils.TAG_PREFIX_EXPORT_IMPORT_METADATA}.experiment_name"]

    for k,v in utils.strip_underscores(run1.info).items():
        assert str(v) == source_tags2[f"{utils.TAG_PREFIX_EXPORT_IMPORT_RUN_INFO}.{k}"],f"Assert failed for RunInfo field '{k}'" # NOTE: tag values must be strings

    compare_runs(client_src, client_dst, run1, run2, output_dir)


def compare_runs(client_src, client_dst, run1, run2, output_dir):
    _compare_common_tags(run1, run2)
    _compare_runs_without_tags(client_src, client_dst, run1, run2, output_dir)


def _compare_common_tags(run1, run2):
    tags1 = { k:v for k,v in run1.data.tags.items() if not k.startswith("mlflow") }
    tags2 = { k:v for k,v in run2.data.tags.items() if not k.startswith("mlflow") }
    assert tags1 == tags2


def _compare_runs_without_tags(client_src, client_dst, run1, run2, output_dir):
    run_artifact_dir1, run_artifact_dir2 = utils_test.create_run_artifact_dirs(output_dir)
    _compare_run_info(run1, run2)
    _compare_data(run1, run2)
    _compare_artifacts(client_src, client_dst, run1, run2, run_artifact_dir1, run_artifact_dir2)


def _compare_run_info(run1, run2):
    assert run1.info.lifecycle_stage == run2.info.lifecycle_stage
    assert run1.info.status == run2.info.status


def _compare_data(run1, run2):
    assert run1.data.params == run2.data.params
    assert run1.data.metrics == run2.data.metrics
    _compare_common_tags(run1, run2)


def _compare_artifacts(client_src, client_dst, run1, run2, run_artifact_dir1, run_artifact_dir2):
    path1 = client_src.download_artifacts(run1.info.run_id, ".", dst_path=run_artifact_dir1)
    path2 = client_dst.download_artifacts(run2.info.run_id, ".", dst_path=run_artifact_dir2)
    assert utils_test.compare_dirs(path1, path2)


def compare_models(mlflow_client_src, mlflow_client_dst, model_src, model_dst, output_dir):
    assert model_src.description == model_dst.description
    assert model_src.tags == model_dst.tags
    for (vr_src, vr_dst) in zip(model_src.latest_versions, model_dst.latest_versions):
        compare_versions(mlflow_client_src, mlflow_client_dst, vr_src, vr_dst, output_dir)


def compare_versions(mlflow_client_src, mlflow_client_dst, vr_src, vr_dst, output_dir):
    assert vr_src.current_stage == vr_dst.current_stage
    assert vr_src.description == vr_dst.description
    if mlflow_client_src != mlflow_client_src:
        assert vr_src.name == vr_dst.name
    assert vr_src.status == vr_dst.status
    assert vr_src.status_message == vr_dst.status_message
    if not utils.importing_into_databricks():
        assert vr_src.user_id == vr_dst.user_id
    assert vr_src.run_id != vr_dst.run_id
    run_src = mlflow_client_src.get_run(vr_src.run_id)
    run_dst = mlflow_client_dst.get_run(vr_dst.run_id)
    compare_runs(mlflow_client_src, mlflow_client_dst, run_src, run_dst, output_dir)


def dump_runs(run1, run2):
    from mlflow_export_import.common.dump_run import dump_run
    print("======= Run1")
    dump_run(run1)
    print("======= Run2")
    dump_run(run2)
