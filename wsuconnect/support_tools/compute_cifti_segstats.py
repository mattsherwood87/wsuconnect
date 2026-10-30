#!/opt/conda/envs/aslprep/bin/python3.11
# zmap_cifti_wf.py

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 5 November 2025
#
# This file runs in the python enviroment on pennlinc/aslprep docker image. Must bind mount /resshare/wsuconnect to /resshare/wsuconnect.
#
#versioning

# """
# COMPUTE_SEGSTATS_FSLR WORKFLOW
# ++++++++++++++++++++

# .. autofunction:: init_segstats_wf

# """
import os
import sys
aslprep_dir = "/opt/conda/envs/aslprep/lib/python3.11/site-packages"  # replace * with actual version
if os.path.exists(aslprep_dir):
    sys.path.insert(0, aslprep_dir)


from nipype import config, logging
config.enable_debug_mode()
logging.update_logging(config)
from bids.layout import Config, parse_file_entities
from bids.layout.writing import build_path
from json import loads
from niworkflows.engine.workflows import LiterateWorkflow as Workflow
from niworkflows.interfaces.bids import DerivativesDataSink as BaseDerivativesDataSink
from pathlib import Path



# REALPATH = '/resshare'
# if not REALPATH in sys.path:
#     sys.path.append(REALPATH)
from wsuconnect.data import load as load_data
from wsuconnect.classes.workbench import *
import argparse


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




#parse command-line arguments
parser = argparse.ArgumentParser('compute_segstats_fsLR.py: compute segmentation statistics from surface fsLR space')
parser.add_argument('--data-dir',action='store',dest='DATA_DIR',help="Path to the project's directory",required=True)
# parser.add_argument('--subject-id',action='store',dest='SUBJECTID',help='participant ID')
parser.add_argument('--in-file',action='store',dest='IN_FILE',help='input cifti dtseries/dtscalar file in fsLR space',required=True)
parser.add_argument('--label-file',action='store',dest='LABEL_FILE',help='input cifti dtseries/dtscalar file in fsLR space',required=True)
parser.add_argument('--datatype',action='store',dest='DATATYPE',help='input cifti dtseries/dtscalar file in fsLR space',required=True)
parser.add_argument('--threshold',action='store',dest='THRESHOLD',help='input cifti dtseries/dtscalar file in fsLR space',default=0)
parser.add_argument('--exclude-outliers',action='store',dest='EXCLUDE_OUTLIERS',help='input cifti dtseries/dtscalar file in fsLR space',default=0)



class DerivativesDataSink(BaseDerivativesDataSink):
    """Store derivative files.
    A child class of the niworkflows DerivativesDataSink, using aslprep's configuration files.
    """

    out_path_base = ''
    _allowed_entities = set(config_entities)
    _config_entities = config_entities
    _config_entities_dict = merged_entities
    _file_patterns = connect_spec['default_path_patterns']

    def _build_path(self, entities, pattern=None):
        print(entities)
        # if "datatype" in entities and entities["datatype"] == "perf":
        #     # Prepend a slash to satisfy the regex
        #     entities["datatype"] = f"/{entities['datatype']}/"
        return super()._build_path(entities, pattern)


def init_compute_cifti_segstats_wf(datadir: str, in_file: Path, label_file: str, datatype: str, threshold: float=None, exclude_outliers: float=None) -> Workflow:
    """
    init_compute_cifti_segstats_wf _summary_

    _extended_summary_

    Parameters
    ----------
    datadir : str
        _description_
    in_file : Path
        _description_
    label_file : str
        _description_
    threshold : float, optional
        _description_, by default 0
    exclude_outliers : float, optional
        _description_, by default 0

    Returns
    -------
    Workflow
        _description_
    """


    import glob
    from nipype.interfaces.ants import ApplyTransforms
    from nipype.pipeline import engine as pe
    from nipype.interfaces.utility import Function
    from fmriprep.workflows.bold.resampling import init_bold_fsLR_resampling_wf, init_bold_grayords_wf
    from smriprep.interfaces.templateflow import TemplateFlowSelect
    from niworkflows.utils.spaces import Reference
    from bids.layout import parse_file_entities

    #output mean text file to derivatives folder
    filename = os.path.basename(in_file)
    labels = parse_file_entities(filename)

    deriv_dir = Path(os.path.join(datadir, 'derivatives'))

    # create base workflow with working folder from participant zmap
    wf = Workflow(name="compute_cifti_segstats_wf", 
                        base_dir=os.path.join(in_file.parent,f"{str(in_file.name).split('.',1)[0]}.work")
    )

    # create expression
    if not threshold:
        expStr = "A"
        expStr_mask = "1 + (0 * A)"
    else:
        expStr = f"A * (A >= {threshold})"
        expStr_mask = f"(A >= {threshold})"

    # threshold input cifti and create a mask of thresholded vertices
    cifti_threshold = pe.Node(
        CiftiMath(
            expression=expStr,
            A_file=in_file,
            cifti_out="thresh.dscalar.nii"
        ),
        name='ciftimath_threshold'
    )

    cifti_mask = pe.Node(
        CiftiMath(
            expression=expStr_mask,
            A_file=in_file,
            cifti_out="mask.dscalar.nii"),
        name='ciftimath_threshold_mask',
    )

    # parcellate the using SUM for thresholded cifti and masked cifti
    glasser = load_data('glasser')
    if not exclude_outliers:
        cifti_threshold_parcellate = pe.Node(
            CiftiParcellate(
                direction="COLUMN",
                method="SUM",
                cifti_out="sum_above.ptseries.nii",
                non_empty_mask_out="threshold_mask.pscalar.nii"),
            name='ciftiparcellate_threshold_sum',
        )
    else:
        cifti_threshold_parcellate = pe.Node(
            CiftiParcellate(
                direction="COLUMN",
                method="SUM",
                cifti_out="SUM_above.ptseries.nii",
                exclude_outliers=(exclude_outliers,exclude_outliers),
                non_empty_mask_out="threshold_mask.pscalar.nii"),
            name='ciftiparcellate_threshold_sum',
        )
    cifti_threshold_parcellate.inputs.cifti_label = str(glasser / label_file)
    wf.connect([(cifti_threshold, cifti_threshold_parcellate, [("out_file", "cifti_in")])])


    # don't need to exclude_outliers for the mask, all values are 1
    cifti_mask_parcellate = pe.Node(
        CiftiParcellate(
            direction="COLUMN",
            method="SUM",
            cifti_out="count_above.ptseries.nii",
            non_empty_mask_out="threshold_count_mask.pscalar.nii"),
        name='ciftiparcellate_threshold_mask_sum',
    )
    cifti_mask_parcellate.inputs.cifti_label = str(glasser / label_file)
    wf.connect([(cifti_mask, cifti_mask_parcellate, [("out_file", "cifti_in")])])

    # convert to text and save to derivatives
    cifti_convert_count = pe.Node(
        CiftiConvertToText(
            text_out="count_above.ptseries.txt",
            col_delim=","),
        name="cifticonvert_threshold_mask_to_text",
    )
    wf.connect([(cifti_mask_parcellate,cifti_convert_count, [("out_file","cifti_in")])])

    ds_cifti_count = pe.Node(
        DerivativesDataSink(
            base_directory=str(deriv_dir),
            out_path_base=".",
            desc=f"count{labels['desc']}",
            compress=False,
            dismiss_entities=['den'],
            source_file=str(in_file),
            datatype=datatype),
        name="ds_cifti_threshold_mask"
    )
    wf.connect([(cifti_convert_count, ds_cifti_count, [("out_file", "in_file")])])
    
    # compute average by dividing total above threshold by the number of vertices in each parcel
    cifti_mean = pe.Node(
        CiftiMath(
            expression="A / B",
            cifti_out="mean.ptseries.nii"),
        name="ciftimath_threshold_mean",
    )
    wf.connect([
        (cifti_threshold_parcellate, cifti_mean, [("out_file", "A_file")]),
        (cifti_mask_parcellate, cifti_mean, [("out_file", "B_file")]),
    ])

    # convert average to a text file
    cifti_convert = pe.Node(
        CiftiConvertToText(
            text_out="mean.ptseries.txt",
            col_delim=","),
        name="cifticonvert_threshold_mean_to_text",
    )
    wf.connect([(cifti_mean, cifti_convert, [("out_file","cifti_in")])])

    ds_cifti_mean = pe.Node(
        DerivativesDataSink(
            base_directory=str(deriv_dir),
            out_path_base=".",
            desc=f"mean{labels['desc']}",
            compress=False,
            dismiss_entities=['den'],
            source_file=str(in_file),
            datatype=datatype),
        name="ds_cifti_threshold_mean"
    )
    wf.connect([(cifti_convert, ds_cifti_mean, [("out_file", "in_file")])])


    # compute total number of vertices
    cifti_total = pe.Node(
        CiftiMath(
            expression="1 + (0 * A)",
            A_file=in_file,
            cifti_out="total.dscalar.nii"),
        name='ciftimath_total_vertices',
    )

    # sum number of vertices per parcel
    cifti_total_parcellate = pe.Node(
        CiftiParcellate(
            direction="COLUMN",
            method="SUM",
            cifti_out="total_above.ptseries.nii",
            non_empty_mask_out="total_mask.pscalar.nii"),
        name='ciftiparcellate_total_vertices',
    )
    cifti_total_parcellate.inputs.cifti_label = str(glasser / label_file)
    wf.connect([(cifti_total, cifti_total_parcellate, [("out_file", "cifti_in")])])


    # if using a threshold, compute average per parcel unthresholded
    if threshold:
        cifti_nothreshold_parcellate = pe.Node(
            CiftiParcellate(
                direction="COLUMN",
                method="MEAN",
                cifti_in=in_file,
                cifti_out="nothreshold_mean.ptseries.nii"),
            name='ciftiparcellate_nothreshold_sum',
        )
        cifti_nothreshold_parcellate.inputs.cifti_label = str(glasser / label_file)

        # convert to text and save to derivatives
        cifti_convert_total_mean = pe.Node(
            CiftiConvertToText(
                text_out="nothreshold_mean.ptseries.txt",
                col_delim=","),
            name="cifticonvert_nothreshold_mean_to_text",
        )
        wf.connect([(cifti_nothreshold_parcellate,cifti_convert_total_mean, [("out_file","cifti_in")])])

        ds_cifti_total_mean = pe.Node(
            DerivativesDataSink(
                base_directory=str(deriv_dir),
                out_path_base=".",
                desc=f"nothreshmean{labels['desc']}",
                compress=False,
                dismiss_entities=['den'],
                source_file=str(in_file),
                datatype=datatype),
            name="ds_cifti_nothresh_mean"
        )
        wf.connect([(cifti_convert_total_mean, ds_cifti_total_mean, [("out_file", "in_file")])])

    # compute the percent of parcel above threshold
    cifti_math_percent = pe.Node(
        CiftiMath(
            expression="100*( A / B )",
            cifti_out="percent_above.ptseries.nii"),
        name="ciftimath_percent_above_thresh",
    )
    wf.connect([
        (cifti_total_parcellate, cifti_math_percent, [("out_file", "B_file")]),
        (cifti_mask_parcellate, cifti_math_percent, [("out_file", "A_file")]),
    ])

    # convert to text and save to derivatives
    cifti_convert_percent = pe.Node(
        CiftiConvertToText(
            text_out="percent_above.ptseries.txt",
            col_delim=","),
        name="cifticonvert_percent_to_text",
    )
    wf.connect([(cifti_math_percent,cifti_convert_percent, [("out_file","cifti_in")])])

    ds_cifti_percent = pe.Node(
        DerivativesDataSink(
            base_directory=str(deriv_dir),
            out_path_base=".",
            desc=f"percent{labels['desc']}",
            compress=False,
            dismiss_entities=['den'],
            source_file=str(in_file),
            datatype=datatype),
        name="ds_cifti_percent"
    )
    wf.connect([(cifti_convert_percent, ds_cifti_percent, [("out_file", "in_file")])])

    

    # wb_command -cifti-math "z * (z >= 1.76)" zstat_thresh.dscalar.nii -var z sub-121201_ses-02_task-nvs_acq-post_run-1_space-fsLR_den-91k_desc-act_zstat.dtseries.nii
    # wb_command -cifti-math "(z >= 1.76)" zstat_thresh_mask.dscalar.nii -var z sub-121201_ses-02_task-nvs_acq-post_run-1_space-fsLR_den-91k_desc-act_zstat.dtseries.nii
    # wb_command -cifti-parcellate zstat_thresh.dscalar.nii /resshare/wsuconnect/templateflow/glasser/Q1-Q6_RelatedParcellation210/MNINonLinear/fsaverage_LR32k/Q1-Q6_RelatedParcellation210.CorticalAreas_dil_Colors_210P_Orig.32k_fs_LR.dlabel.nii COLUMN sum_above.ptseries.nii -method SUM
    # wb_command -cifti-parcellate zstat_thresh_mask.dscalar.nii /resshare/wsuconnect/templateflow/glasser/Q1-Q6_RelatedParcellation210/MNINonLinear/fsaverage_LR32k/Q1-Q6_RelatedParcellation210.CorticalAreas_dil_Colors_210P_Orig.32k_fs_LR.dlabel.nii COLUMN count_above.ptseries.nii -method SUM
    # wb_command -cifti-math "sum_above / count" mean_zstat_thresh.ptseries.nii -var sum_above sum_above.ptseries.nii -var count count_above.ptseries.nii
    # wb_command -cifti-convert -to-text mean_zstat_thresh.ptseries.nii mean_zstat_thresh.ptseries.txt
    # wb_command -cifti-math "(100 * count_above / count_total)" percent_zstat_thresh.ptseries.nii -var count_above count_above.ptseries.nii -var count_total count_total.ptseries.nii
    # wb_command -cifti-convert -to-text percent_zstat_thresh.ptseries.nii percent_zstat_thresh.ptseries.txt
    # wb_command -cifti-convert -to-text count_total.ptseries.nii count_total.ptseries.txt
    # wb_command -cifti-convert -to-text count_above.ptseries.nii count_above.ptseries.txt
    
    return wf


if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """
    options = parser.parse_args()
    wf = init_compute_cifti_segstats_wf(
        datadir=options.DATA_DIR, 
        in_file=Path(options.IN_FILE), 
        label_file=options.LABEL_FILE, 
        datatype=options.DATATYPE, 
        threshold=options.THRESHOLD, 
        exclude_outliers=options.EXCLUDE_OUTLIERS
    )#, subject=options.SUBJECTID))

    wf.write_graph(graph2use='flat', format='png')
    # for node in wf._get_all_nodes():
    #     print(f"Node: {node.name}")
    #     try:
    #         print(node.interface.cmdline)
    #     except Exception as e:
    #         print("\tWARNING: could not generate cmdline:", e)
    #     print("-" * 60)
    result = wf.run(plugin_args={'overwrite': True})

    print("-" * 60)
    for node_res in result.nodes():
        print(f"Node: {node_res.name}")
        runtime = getattr(node_res.result, "runtime", None)
        if runtime:
            # runtime is a Bunch
            cmdline = getattr(runtime, "cmdline", None)
            if cmdline:
                print(cmdline)
        print("-" * 60)