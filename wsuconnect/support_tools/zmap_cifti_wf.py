#!/opt/conda/envs/aslprep/bin/python3.11
# zmap_cifti_wf.py

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 5 November 2025
#
# This file runs in the python enviroment on pennlinc/aslprep docker image. Must bind mount /resshare/wsuconnect to /resshare/wsuconnect.
#
#versioning

# """
# ZMAP CIFTI workflow
# ++++++++++++++++++++

# .. autofunction:: init_zmap_cifti_wf

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
from niworkflows.interfaces.bids import DerivativesDataSink as BaseDerivativesDataSink

import sys
import os
REALPATH = '/resshare'
if not REALPATH in sys.path:
    sys.path.append(REALPATH)
from wsuconnect.data import load as load_data
import argparse
from pathlib import Path

# NOTE: Modified for wsuconnect's purposes
connect_spec = loads(load_data.readable('connect_bids_config.json').read_text())
bids_config = Config.load('bids')
deriv_config = Config.load('derivatives')

connect_entities = {v['name']: v['pattern'] for v in connect_spec['entities']}
merged_entities = {**bids_config.entities, **deriv_config.entities}
merged_entities = {k: v.pattern for k, v in merged_entities.items()}
merged_entities = {**merged_entities, **connect_entities}
merged_entities = [{'name': k, 'pattern': v} for k, v in merged_entities.items()]
config_entities = frozenset({e['name'] for e in merged_entities})

class DerivativesDataSink(BaseDerivativesDataSink):
    """Store derivative files.
    A child class of the niworkflows DerivativesDataSink, using aslprep's configuration files.
    """
    out_path_base = ''
    _allowed_entities = set(config_entities)
    _config_entities = config_entities
    _config_entities_dict = merged_entities
    _file_patterns = connect_spec['default_path_patterns']


#parse command-line arguments
parser = argparse.ArgumentParser('feat_full_firstlevel.py: perform first level FEAT fMRI analysis')
parser.add_argument('--data-dir',action='store',dest='DATADIR',help='bold zstat file in native space')
parser.add_argument('--subject-id',action='store',dest='SUBJECTID',help='bold zstat file in native space')
parser.add_argument('--bold-file',action='store',dest='BOLDFILE',help='bold zstat file in native space')

def init_zmap_cifti_wf(datadir: str, subject: str, bold_file: Path):
    """creates a workflow to sample a Z-statistic map on the fsLR surface

    Args:
        project (str): project identienfier
        bold_file (Path): zstat image in native BOLD space

    Returns:
        niworkflows.engine.workflows.LiterateWorkflow: workflow for generating zmap CIFTI surface dtseries file in fsLR space
    """
    import glob
    from nipype.interfaces.ants import ApplyTransforms
    from nipype.pipeline import engine as pe
    from fmriprep.workflows.bold.resampling import init_bold_fsLR_resampling_wf, init_bold_grayords_wf
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow
    from smriprep.interfaces.templateflow import TemplateFlowSelect
    from niworkflows.utils.spaces import Reference
    #grab some basic information
    # creds.read(options.PROJECT)

    deriv_dir = Path(os.path.join(datadir, 'derivatives'))


    # create base workflow with working folder from participant zmap
    workflow = Workflow(name="zmap_cifti_resample_wf", 
                        base_dir=os.path.join(bold_file.parent,f"{str(bold_file.name).split('.',1)[0]}.work")
    )

    #get bold-native to T1wref transform
    filename = bold_file.name
    labels = parse_file_entities(filename)
    if 'extension' in labels:
        labels['extension'] = labels['extension'].lstrip('.')
    if 'desc' in labels:
        labels['description'] = labels.pop('desc')
    labels['description'] = 'coreg'
    labels['from'] = 'boldref'
    labels['to'] = 'T1w'
    labels['mode'] = 'image'
    labels['suffix'] = 'xfm'
    labels['extension'] = 'txt'
    labels['subject'] = subject
    template = "sub-{subject}[_ses-{session}][_task-{task}][_acq-{acquisition}][_ce-{ceagent}][_dir-{direction}][_rec-{reconstruction}][_run-{run}][_echo-{echo}][_space-{space}][_res-{resolution}][_den-{density}][_cohort-{cohort}][_from-{from}_to-{to}_mode-{mode}][_desc-{description}]_{suffix}.{extension}"
    filename = build_path(labels,template)

    #transform zmap from bold-native to T1wref
    z2t1ref = pe.Node(ApplyTransforms(dimension=3,
                                      interpolation="LanczosWindowedSinc",
                                      float=True,
                                      input_image_type=3,
                                      args="-v",
                                      input_image=bold_file,
                                      reference_image=str(deriv_dir / f"sub-{subject}" / "anat" / f"sub-{subject}_desc-preproc_T1w.nii.gz"),
                                      transforms=str(deriv_dir / f"sub-{subject}" / f"ses-{labels['session']}" / "func" / filename)
                                      ),
                      name="zmap_to_t1ref_wf",
    )

    #output zmap in T1wref space to derivatives folder
    ds_zmap_t1w = pe.Node(DerivativesDataSink(base_directory=str(deriv_dir),
                                              out_path_base=".",
                                              desc="act",
                                              suffix="zstat",
                                              space="T1w",
                                              compress=True,
                                              source_file=str(bold_file),
                                              datatype="func"),
                          name="ds_zmap_t1w"
    )
    workflow.connect([(z2t1ref, ds_zmap_t1w, [("output_image", "in_file")])])


    #register zmap to fsLR space
    fsLR_wf = init_bold_fsLR_resampling_wf(grayord_density="91k",mem_gb=1,omp_nthreads=1,name="zmap_fsLR_resample_wf")

    #get white surfs
    pattern = str(deriv_dir / f"sub-{subject}" / "anat" / "*hemi-[LR]_white.surf.gii")
    white_surfs = sorted(glob.glob(pattern))
    fsLR_wf.inputs.inputnode.white = white_surfs #use fs_source
    #get pial surfs
    pattern = str(deriv_dir / f"sub-{subject}" / "anat" / "*hemi-[LR]_pial.surf.gii")
    pial_surfs = sorted(glob.glob(pattern))
    fsLR_wf.inputs.inputnode.pial = pial_surfs #use fs_source
    #get midthickness surfs 
    pattern = str(deriv_dir / f"sub-{subject}" / "anat" / "*hemi-[LR]_midthickness.surf.gii")
    mt_surfs = sorted(glob.glob(pattern))
    fsLR_wf.inputs.inputnode.midthickness = mt_surfs
    #get cortex mask label
    pattern = str(deriv_dir / f"sub-{subject}" / "anat" / "*hemi-[LR]_desc-cortex_mask.label.gii")
    cortexMask_labels = sorted(glob.glob(pattern))
    fsLR_wf.inputs.inputnode.cortex_mask = cortexMask_labels
    #get sphere_reg_fsLR surfs
    pattern = str(deriv_dir / f"sub-{subject}" / "anat" / "*hemi-[LR]_space-fsLR_desc-reg_sphere.surf.gii")
    sphere_reg_fsLR = sorted(glob.glob(pattern))
    fsLR_wf.inputs.inputnode.sphere_reg_fsLR = sphere_reg_fsLR
    #get midthickness_resampled surfs
    pattern = str(deriv_dir / f"sub-{subject}" / "anat" / "*hemi-[LR]_space-fsLR_den-32k_midthickness.surf.gii")
    midthickness_fsLR = sorted(glob.glob(pattern))
    fsLR_wf.inputs.inputnode.midthickness_fsLR = midthickness_fsLR


    workflow.connect([(z2t1ref, fsLR_wf, [("output_image", "inputnode.bold_file")])])
    #workflow.connect([(fs_source, fsLR_wf, [("subjects_dir", "input_node.subjects_dir"), ("subject_id", "inputnode.subject_id")])])

    grayords_wf = init_bold_grayords_wf(grayord_density="91k",mem_gb=1,repetition_time=2,name="zmap_grayords_wf")
    workflow.connect([(fsLR_wf, grayords_wf, [("outputnode.bold_fsLR", "inputnode.bold_fsLR")])])

    
    pattern = str(deriv_dir / f"sub-{subject}" / "anat" / "*from-T1w_to-MNI152NLin6Asym_mode-image_xfm.h5")
    t1ref_to_MNI6_xfm = glob.glob(pattern)
    warp_zt1ref_to_MNI6 = pe.Node(ApplyTransforms(dimension=3,
                                                  interpolation="LanczosWindowedSinc",
                                                  float=True,
                                                  input_image_type=3,
                                                  args="-v",
                                                  transforms=t1ref_to_MNI6_xfm),
                                  name=f'zt1ref2MNI6',
                                  mem_gb=1
    )


    ds_zmap_MNI6 = pe.Node(DerivativesDataSink(base_directory=str(deriv_dir),
                                               out_path_base=".",
                                               desc="act",
                                               suffix="zstat",
                                               space="MNI152NLin6Asym",
                                               compress=True,
                                               source_file=str(bold_file),
                                               datatype="func"),
                           name="ds_zmap_MNI6"
    )
    workflow.connect([(warp_zt1ref_to_MNI6, ds_zmap_MNI6, [("output_image", "in_file")])])

    ref = Reference('MNI152NLin6Asym',{'res': 2})
    select_MNI6_tpl = pe.Node(TemplateFlowSelect(template=ref.fullname,
                                                 resolution=ref.spec['res']),
                              name='select_MNI6_tpl')
    workflow.connect([(select_MNI6_tpl, warp_zt1ref_to_MNI6, [("brain_mask", "reference_image")])])
    workflow.connect([(z2t1ref, warp_zt1ref_to_MNI6, [("output_image", "input_image")])])
    workflow.connect([(warp_zt1ref_to_MNI6, grayords_wf, [("output_image", "inputnode.bold_std")])])

    ds_zmap_cifti = pe.Node(DerivativesDataSink(base_directory=str(deriv_dir),
                                                out_path_base=".",
                                                desc="act",
                                                suffix="zstat",
                                                space="fsLR",
                                                density="91k",
                                                compress=False,
                                                source_file=str(bold_file),
                                                datatype="func"),
                            name="ds_zmap_cifti"
    )

    workflow.connect([(grayords_wf, ds_zmap_cifti, [("outputnode.cifti_bold", "in_file")])])
    return workflow


if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """
    options = parser.parse_args()
    wf = init_zmap_cifti_wf(datadir=options.DATADIR, subject=options.SUBJECTID, bold_file=Path(options.BOLDFILE))
    wf.write_graph(graph2use='flat', format='png')
    wf.run()