function enigma_qc_step2_fun(FS_directory,QC_output_directory)
%% Here's a simple MATLAB loop to loop through all the subjects and create PNG images for QC!!
%% Please note if you have a grid system to parallel process your images, you can also use a compiled version of the matlab code and run it across the grid. Contact us enigma@ini.usc.edu if you have questions on how.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%USER DEFINED INPUTS
%Choose "FS_directory" so that it selects only your subject folders that contain FS output
%"QC_output_directory" should be a folder you want to output your QC PNGS, we suggest just creating a folder within the FreeSurfer directory if you have writing permissions there!
%"ENIGMA_QC_folder" should be the path to the folder where you have downloaded the ENIGMA QC zip folder and unzipped. You may already be running this script from that folder, but just in case you are not, we will 'addpath' to that folder such that all functions can be used.
 
% FS_directory=;
% QC_output_directory='/resshare/projects/2022_KBR_Cog_Neuro_2/measurement_stability/derivatives/recon-all/QC/';
ENIGMA_QC_folder='/resshare/general_processing_scripts/helper_functions/ENIGMA_Cortical_QC_2.0';
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
addpath(ENIGMA_QC_folder)
%%%%% some variable changes: %%%%%
% inDirectory: previously 'a'
% subjectID: previously 'b'
% i: previously 'x' 
 
% 'dir' will list all folders in the directory, so we need to start indexing from 3 as 1 and 2 will correspond to "." and ".." which correspond to the current directory and its parent directory 
 
inDirectory=dir(char(strcat(FS_directory,'/sub-*')));
N=size(inDirectory,1);
 
%% if this errors out, change the N below to 3 and remove the semicolons ';' at the end of the 'T1mgz' and 'APSmgz' to check and make sure those paths exist!!
 
for i = 1:N
    [c,subjectID,d]=fileparts(inDirectory(i,1).name); 
    try
    T1mgz=[FS_directory, '/', subjectID, '/mri/orig_nu.mgz'];
    %T1mgz=[FS_directory, '/', subjectID, '/mri/rawavg.mgz'];
    APSmgz=[FS_directory,'/', subjectID, '/mri/aparc+aseg.mgz'];
        func_make_corticalpngs_ENIGMA_QC( QC_output_directory, subjectID, T1mgz ,APSmgz );
    end
    display(['Done with subject: ', subjectID, ': ', num2str(i), ' of ', num2str(N)]);
end
 
%%% Now you should be ready to view the website!! %%%%
end