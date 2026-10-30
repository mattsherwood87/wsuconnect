

from niworkflows.interfaces.bids import DerivativesDataSink as BaseDerivativesDataSink
import os as _os
from pathlib import Path as _Path
_REALPATH = _Path(_os.path.realpath(__file__)).parts[:-2]

class DerivativesDataSink(BaseDerivativesDataSink):
    """Store derivative files.
    A child class of the niworkflows DerivativesDataSink, using aslprep's configuration files.
    """
    import sys
    from pathlib import Path
    from json import loads
    from bids.layout import Config
    if not _REALPATH in sys.path:
        sys.path.append(_REALPATH)
    from wsuconnect.data import load as load_data

    # NOTE: Modified for wsuconnect's purposes
    connect_spec = loads(load_data.readable('connect_bids_config.json').read_text())
    bids_config = Config.load('bids')
    deriv_config = Config.load('derivatives')

    connect_entities = {v['name']: v['pattern'] for v in connect_spec['entities']}
    merged_entities = {**bids_config.entities, **deriv_config.entities}
    merged_entities = {k: v.pattern for k, v in merged_entities.items()}
    merged_entities = {**merged_entities, **connect_entities}
    # merged_entities = {**connect_entities}
    merged_entities = [{'name': k, 'pattern': v} for k, v in merged_entities.items()]
    config_entities = frozenset({e['name'] for e in merged_entities})

    out_path_base = ''
    _allowed_entities = set(config_entities)
    _config_entities = config_entities
    _config_entities_dict = merged_entities
    _file_patterns = connect_spec['default_path_patterns']