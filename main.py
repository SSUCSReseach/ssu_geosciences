# surpress tensorflow warnings
import os 
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # log minimum errors to the user

# import our passed number of gpus by user
from config import gpu_to_use as gtu
from config import num_gpus as ngpu

if ngpu == 1:
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gtu - 1)
elif ngpu == 0:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    
import tensorflow as tf

from tools.kt_utils import *
from tools.training import *
from model import *

import numpy as np
import keras
from keras import backend as K
from keras.preprocessing.image import ImageDataGenerator

from sklearn.model_selection import StratifiedKFold
from sklearn.utils import class_weight



def main(loaded_params):

    model_name = loaded_params['model_name']
    num_epochs = loaded_params['num_epochs']
    batch_size = loaded_params['batch_size']
    ratio_train = loaded_params['ratio_train']
    ratio_test = loaded_params['ratio_test']
    learning_rate = loaded_params['learning_rate']
    output_directory = loaded_params['output_directory']
    optimizer = loaded_params['optimizer']
    image_directory = loaded_params['image_directory']
    num_gpus = loaded_params['num_gpus']
    k_folds = loaded_params['k_folds']
    use_class_weights = loaded_params['use_class_weights']
    use_oversampling = loaded_params['use_oversampling']
    use_data_augmentation = loaded_params['use_data_augmentation']
    use_attention_networks = loaded_params['use_attention_networks']

    
    base_model, img_size = load_base_model(model_name)

    # load our images
    X_train_orig, Y_train_orig, X_dev_orig, Y_dev_orig, X_test_orig, Y_test_orig  = load_dataset(image_directory, img_size, ratio_train=ratio_train, ratio_test = ratio_test, use_data_augmentation=use_data_augmentation)

    # Normalize image vectors
    X_train = X_train_orig/255.
    X_dev = X_dev_orig/255.
    X_test = X_test_orig/255.

    # Rename
    Y_train = Y_train_orig
    Y_dev = Y_dev_orig
    Y_test = Y_test_orig

    
    print_shapes(X_train, Y_train, X_dev, Y_dev, X_test, Y_test)

    
    if k_folds == None or k_folds <= 1:
        print("building model")
        completed_model = create_final_layers(base_model,
                                          img_size,
                                          learning_rate=learning_rate,
                                          optimizer=optimizer, num_gpus=num_gpus)
        print('finished building model\nTraining Model')
        history = train_and_evaluate_model(completed_model,
                                           X_train,
                                           Y_train,
                                           X_dev,
                                           Y_dev,
                                           batch_size=batch_size,
                                           num_epochs=num_epochs,
                                           use_class_weights=use_class_weights)

        save_results(output_directory, model_name, history)
    else:

        # for k-fold we must combine our data into a single entity.
        data = np.concatenate((X_train, X_dev), axis=0)
        labels = np.concatenate((Y_train, Y_dev), axis=0)

        
        skf = StratifiedKFold(n_splits = k_folds, shuffle=False)
        scores = np.zeros(k_folds)
        idx = 0
        
        for (train, test) in skf.split(data,labels):
            print ("Running Fold", idx+1, "/", k_folds)
            completed_model = None

            completed_model = create_final_layers(base_model,
                                                  img_size,
                                                  learning_rate=learning_rate,
                                                  optimizer=optimizer,
                                                  num_gpus=num_gpus)
            start = time.time()
            preds, scores[idx] = k_fold(completed_model,
                                       data[train], labels[train],
                                        data[test], labels[test],
                                        batch_size=batch_size,
                                        num_epochs=num_epochs,
                                        use_class_weights=use_class_weights)

            print("time to k_fold: ", str(time.time()-start))
            idx += 1
            cm = confusion_matrix(labels[test],
                                           preds, labels=[0,1])
                                           
            print_cm(cm, labels=['Negative', 'Positive'])
            
        print("\nscores: ", str(scores))
        print("mean: ", str(scores.mean()))

        






    
if __name__ == "__main__":
    
    import time
    start = time.time()
    loaded_params = parse_config_file()
    initialize_output_directory(loaded_params['output_directory'],
                                loaded_params['model_name'])


    main(loaded_params)
    end = time.time()
    print("total elapsed time: ", str(end -start))

    # stop the session from ending after main has finished, exit gracefully
    K.clear_session() 



