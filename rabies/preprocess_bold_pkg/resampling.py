from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu

from .utils import slice_applyTransforms, init_bold_reference_wf, Merge
from nipype.interfaces.utility import Function

def init_bold_preproc_trans_wf(isotropic_resampling, upsampling, data_type='float64', name='bold_preproc_trans_wf'):
    """
    This workflow resamples the input fMRI in its native (original)
    space in a "single shot" from the original BOLD series.
    """
    workflow = pe.Workflow(name=name)
    inputnode = pe.Node(niu.IdentityInterface(fields=[
        'name_source', 'bold_file', 'motcorr_params', 'transforms_list', 'inverses', 'ref_file']),
        name='inputnode'
    )

    outputnode = pe.Node(
        niu.IdentityInterface(fields=['bold', 'bold_ref']),
        name='outputnode')


    bold_transform = pe.Node(slice_applyTransforms(), name='bold_transform')
    bold_transform.inputs.apply_motcorr = True
    bold_transform.inputs.isotropic_resampling = isotropic_resampling
    bold_transform.inputs.upsampling = upsampling
    bold_transform.inputs.data_type = data_type

    merge = pe.Node(Merge(), name='merge')
    merge.inputs.data_type = data_type
    #merge.plugin_args = {'qsub_args': '-pe smp 2 -l h_vmem=1G ', 'overwrite': True}

    # Generate a new BOLD reference
    bold_reference_wf = init_bold_reference_wf()

    workflow.connect([
        (inputnode, merge, [('name_source', 'header_source')]),
        (inputnode, bold_transform, [
            ('bold_file', 'in_file'),
            ('motcorr_params', 'motcorr_params'),
            ('transforms_list', 'transforms'),
            ('inverses', 'inverses'),
            ('ref_file', 'ref_file'),
            ]),
        (bold_transform, merge, [('out_files', 'in_files')]),
        (merge, bold_reference_wf, [('out_file', 'inputnode.bold_file')]),
        (merge, outputnode, [('out_file', 'bold')]),
        (bold_reference_wf, outputnode, [
            ('outputnode.ref_image', 'bold_ref')]),
    ])

    return workflow


def init_bold_commonspace_trans_wf(isotropic_resampling, upsampling, data_type='float64', name='bold_commonspace_trans_wf'):
    import os
    from .confounds import MaskEPI

    workflow = pe.Workflow(name=name)
    inputnode = pe.Node(niu.IdentityInterface(fields=[
        'name_source', 'bold_file', 'transforms_list', 'inverses']),
        name='inputnode'
    )

    outputnode = pe.Node(
        niu.IdentityInterface(fields=['bold', 'bold_ref', 'brain_mask', 'WM_mask', 'CSF_mask', 'labels']),
        name='outputnode')

    bold_transform = pe.Node(slice_applyTransforms(), name='bold_transform')
    bold_transform.inputs.ref_file = os.environ["template_anat"]
    bold_transform.inputs.apply_motcorr = False
    bold_transform.inputs.isotropic_resampling = isotropic_resampling
    bold_transform.inputs.upsampling = upsampling
    bold_transform.inputs.data_type = data_type

    merge = pe.Node(Merge(), name='merge')
    merge.inputs.data_type = data_type

    # Generate a new BOLD reference
    bold_reference_wf = init_bold_reference_wf()


    WM_mask_to_EPI=pe.Node(MaskEPI(), name='WM_mask_EPI')
    WM_mask_to_EPI.inputs.name_spec='commonspace_WM_mask'
    WM_mask_to_EPI.inputs.mask=os.environ["WM_mask"]

    CSF_mask_to_EPI=pe.Node(MaskEPI(), name='CSF_mask_EPI')
    CSF_mask_to_EPI.inputs.name_spec='commonspace_CSF_mask'
    CSF_mask_to_EPI.inputs.mask=os.environ["CSF_mask"]

    brain_mask_to_EPI=pe.Node(MaskEPI(), name='Brain_mask_EPI')
    brain_mask_to_EPI.inputs.name_spec='commonspace_brain_mask'
    brain_mask_to_EPI.inputs.mask=os.environ["template_mask"]

    propagate_labels=pe.Node(MaskEPI(), name='prop_labels_EPI')
    propagate_labels.inputs.name_spec='commonspace_anat_labels'
    propagate_labels.inputs.mask=os.environ["atlas_labels"]


    workflow.connect([
        (inputnode, merge, [('name_source', 'header_source')]),
        (inputnode, bold_transform, [
            ('bold_file', 'in_file'),
            ('transforms_list', 'transforms'),
            ('inverses', 'inverses'),
            ]),
        (bold_transform, merge, [('out_files', 'in_files')]),
        (merge, bold_reference_wf, [('out_file', 'inputnode.bold_file')]),
        (merge, outputnode, [('out_file', 'bold')]),
        (bold_reference_wf, WM_mask_to_EPI, [
            ('outputnode.ref_image', 'ref_EPI')]),
        (WM_mask_to_EPI, outputnode, [
            ('EPI_mask', 'WM_mask')]),
        (bold_reference_wf, CSF_mask_to_EPI, [
            ('outputnode.ref_image', 'ref_EPI')]),
        (CSF_mask_to_EPI, outputnode, [
            ('EPI_mask', 'CSF_mask')]),
        (bold_reference_wf, brain_mask_to_EPI, [
            ('outputnode.ref_image', 'ref_EPI')]),
        (brain_mask_to_EPI, outputnode, [
            ('EPI_mask', 'brain_mask')]),
        (bold_reference_wf, propagate_labels, [
            ('outputnode.ref_image', 'ref_EPI')]),
        (propagate_labels, outputnode, [
            ('EPI_mask', 'labels')]),
        (bold_reference_wf, outputnode, [
            ('outputnode.ref_image', 'bold_ref')]),
    ])

    return workflow
