from scivision.io import load_dataset, load_pretrained_model, wrapper, _parse_url, _get_model_configs
import intake
import pytest
import fsspec
import xarray
import yaml


def test_parse_url():
    """Test that GitHub urls are correctly converted to raw."""
    path = 'https://github.com/alan-turing-institute/scivision/tests/test_reader.py'
    raw = 'https://raw.githubusercontent.com/alan-turing-institute/scivision/main/tests/test_reader.py'
    assert _parse_url(path) == raw


def test_parse_url_blob():
    """Test that GitHub urls directly copied from a browser are correctly converted to raw."""
    path = 'https://github.com/alan-turing-institute/scivision/blob/main/tests/test_reader.py'
    raw = 'https://raw.githubusercontent.com/alan-turing-institute/scivision/main/tests/test_reader.py'
    assert _parse_url(path) == raw


def test_parse_url_branch():
    """Test that GitHub urls are correctly converted to raw when a branch is specified."""
    # note: test-branch does not exist
    branch = 'test-branch'
    path = 'https://github.com/alan-turing-institute/scivision/tests/test_reader.py'
    raw = 'https://raw.githubusercontent.com/alan-turing-institute/scivision/' + branch + '/tests/test_reader.py'
    assert _parse_url(path, branch=branch) == raw


def test_load_dataset_remote():
    """Test that an intake catalog is generated from scivision-data.yml file in an example GitHub repo."""
    commit_hash = '473a7fd02f4cdd2dd261208a791c7da76cd413a0'
    assert type(load_dataset('https://github.com/alan-turing-institute/intake-plankton', branch=commit_hash)) == intake.catalog.local.YAMLFileCatalog


def test_load_dataset_branch_and_diff_file_name():
    """Test that an intake catalog is generated when specifying a branch AND that a custom file name."""
    branch = 'diff-name-yml'
    assert type(load_dataset('https://github.com/alan-turing-institute/intake-plankton/thESciViSionYAMLfileee.yaml', branch=branch)) == intake.catalog.local.YAMLFileCatalog


def test_load_dataset_local():
    """Test that an intake catalog is generated from a local yml and can be converted to xarray."""
    cat = load_dataset('tests/test_dataset_scivision.yml')
    assert type(cat) == intake.catalog.local.YAMLFileCatalog
    assert type(cat.test_images().to_dask()) == xarray.core.dataarray.DataArray


def test_load_dataset_local_zip():
    """Test that an intake catalog is generated from a local yml which loads from a zip file and can be converted to xarray."""
    cat = load_dataset('tests/test_dataset_scivision_zip.yml')
    assert type(cat) == intake.catalog.local.YAMLFileCatalog
    assert type(cat.test_images().to_dask()) == xarray.core.dataarray.DataArray


def test_load_dataset_from_stac_plugin():
    """Test that an xarray.Dataset can be loaded via the data plugins code and scivision_sentinel2_stac catalog entry"""
    ds = load_dataset('https://github.com/alan-turing-institute/scivision_sentinel2_stac').load_data()
    assert type(ds) == xarray.Dataset


def test_get_model_configs():
    """Test that a config with multiple models is split into separate configs."""
    path = 'tests/test_multiple_models_scivision.yml'
    file = fsspec.open(path)
    with file as config_file:
        stream = config_file.read()
        config = yaml.safe_load(stream)
    config_list = _get_model_configs(config, load_multiple=True)
    for config in config_list:
        assert 'name' in config
        assert 'model' in config


def test_load_pretrained_model_remote():
    """Test that scivision can load a pretrained model from an example GitHub repo."""
    commit_hash = '77bbe037234d11538e46c3ced3d2a5f9294c8468'
    assert type(load_pretrained_model('https://github.com/alan-turing-institute/scivision-test-plugin/.scivision-config_imagenet.yaml', allow_install=True, branch=commit_hash)) == wrapper.PretrainedModel


def test_load_pretrained_model_local():
    """Test that scivision can load a pretrained model from a local yaml that points to a GitHub repo."""
    assert type(load_pretrained_model('tests/test_model_scivision.yml', allow_install=True)) == wrapper.PretrainedModel


def test_load_named_pretrained_model_local():
    """Test that scivision can load a specific model from the given scivision.yml."""
    assert type(load_pretrained_model('tests/test_model_scivision.yml', allow_install=True, model_selection='ImageNetModel')) == wrapper.PretrainedModel
    assert type(load_pretrained_model('tests/test_multiple_models_scivision.yml', allow_install=True, model_selection='ImageNetModel')) == wrapper.PretrainedModel


def test_load_wrong_model_name_raises_value_error():
    """Test that a value error is raised when a model name is specified that doesn't match the model in the config."""
    with pytest.raises(ValueError):
        load_pretrained_model('tests/test_model_scivision.yml', allow_install=True, model_selection='FakeModel')


def test_load_wrong_model_name_raises_value_error_config_has_multiple_models():
    """Test that a value error is raised when a model name is specified that doesn't match one of the models in the config."""
    with pytest.raises(ValueError):
        load_pretrained_model('tests/test_multiple_models_scivision.yml', allow_install=True, model_selection='FakeModel')


def test_load_multiple_models():
    """Test that scivision can load multiple pretrained models from the same GitHub repo."""
    model1, model2 = load_pretrained_model('tests/test_multiple_models_scivision.yml', allow_install=True, load_multiple=True)
    assert type(model1) == wrapper.PretrainedModel
    assert type(model2) == wrapper.PretrainedModel


def test_load_first_model_from_config_with_multiple():
    """Test that scivision loads a single a model from a config with multiple models when not told to load multiple."""
    assert type(load_pretrained_model('tests/test_multiple_models_scivision.yml', allow_install=True, load_multiple=False)) == wrapper.PretrainedModel
