import os
import pickle
import sys 

def process_pickle_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        
        # Check if the expected structure exists
        experiments = data.experiments
        if len(experiments) > 0:
            calibration_loss = experiments[0].calibration_loss
            evaluation_losses = experiments[0].evaluation_losses[0]
            print(f"File: {file_path}, {calibration_loss}, {evaluation_losses}")
        else:
            print(f"File: {file_path} - No experiments found.")
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")

def traverse_and_process(directory):
    for root, dirs, files in os.walk(directory):
        #print(root,dirs,files)
        #for folder in dirs:
        #    traverse_and_process(root+"/"+folder)
        for file in files:
            if file.endswith('.pickled') or file.endswith('.pickle'):  # Adjust extensions as needed
                file_path = os.path.join(root, file)
                process_pickle_file(file_path)

# Replace 'your_directory_path' with the path to the directory you want to scan
your_directory_path = sys.argv[1]
traverse_and_process(your_directory_path)
