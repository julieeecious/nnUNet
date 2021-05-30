import errno
import shutil
import nnunet
import numpy as np
from batchgenerators.utilities.file_and_folder_operations import *
from nnunet.configuration import default_num_threads
from nnunet.utilities.task_name_id_conversion import convert_id_to_task_name
from nnunet.dataset_conversion.utils import generate_dataset_json
from nnunet.paths import nnUNet_raw_data, preprocessing_output_dir
import SimpleITK as sitk
from multiprocessing import Pool


def corrupt_image(filename):
    img_itk = sitk.ReadImage(filename)
    img_npy = sitk.GetArrayFromImage(img_itk)

    dim = img_itk.GetDimension()
    assert dim == 3, "Unexpected dimensionality: %d of file %s, cannot corrupt" % (dim, filename)

    spacing = img_itk.GetSpacing()
    origin = img_itk.GetOrigin()
    direction = np.array(img_itk.GetDirection())

    indices = np.random.random(img_npy.shape) < 0.2
    _img_npy = img_npy.copy()
    _img_npy[indices] = 0 # set to black
    img_itk_new = sitk.GetImageFromArray(_img_npy)
    img_itk_new.SetSpacing(spacing)
    img_itk_new.SetOrigin(origin)
    img_itk_new.SetDirection(direction)

    return img_itk_new
    # sitk.WriteImage(img_itk_new, f'corrupted_{filename}')


def main():
    import argparse
    parser = argparse.ArgumentParser(description="We extend nnUNet to offer self-supervision tasks. This step is to"
                                                 " split the dataset into two - self-supervision input and self- "
                                                 "supervisio output folder.")
    parser.add_argument("-t", type=int, help="Task id. The task name you wish to run self-supervision task for. "
                                                            "It must have a matching folder 'TaskXXX_' in the raw "
                                                            "data folder")
    parser.add_argument("-p", required=False, default=default_num_threads, type=int,
                        help="Use this to specify how many processes are used to run the script. "
                             "Default is %d" % default_num_threads)
    args = parser.parse_args()

    # # local file path for testing
    # base = '/Users/juliefang/Documents/nnUNet_raw_data_base/nnUNet_raw_data/'
    base = join(os.environ['nnUNet_raw_data_base'], 'nnUNet_raw_data')
    # task_name = 'Task002_Heart'
    task_id = args.t
    task_name = convert_id_to_task_name(task_id)
    target_base = join(base, task_name)

    ss_input = "ssInputContextRestoration"
    ss_output = "ssOutputContextRestoration"

    src = join(target_base, "imagesTr")
    target_ss_input = join(target_base, ss_input)  # ssInput - corrupted
    target_ss_output = join(target_base, ss_output)  # ssOutput - original

    maybe_mkdir_p(target_ss_input)
    maybe_mkdir_p(target_ss_output)

    if isdir(target_ss_output):
        shutil.rmtree(target_ss_output)
    shutil.copytree(src, target_ss_output)

    for file in sorted(listdir(src)):
        corrupt_img = corrupt_image(join(src, file))
        corrupt_img_file = 'corrupted_' + str(file)
        corrupt_img_output = join(target_ss_input, corrupt_img_file)
        sitk.WriteImage(corrupt_img, corrupt_img_output)

    assert len(listdir(target_ss_input)) == len(listdir(target_ss_output)) == len(listdir(src)), \
    "Preparation for self-supervision dataset failed. Check again."

if __name__ == "__main__":
    main()
