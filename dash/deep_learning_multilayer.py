import os
import numpy as np
import itertools
import tensorflow as tf
from dash.multilayer_convnet import convnet_variables
import zipfile
import gzip
import time
import pickle
from dash.array_tools import labels_indexes_to_arrays


def train_model(dataDirName):
    # Open training data files
    scriptDirectory = os.path.dirname(os.path.abspath(__file__))
    trainingSet = dataDirName + 'training_set.zip'
    extractedFolder = os.path.join(dataDirName, 'training_set')
    # zipRef = zipfile.ZipFile(trainingSet, 'r')
    # zipRef.extractall(extractedFolder)
    # zipRef.close()
    os.system("unzip %s -d %s" % (trainingSet, extractedFolder))

    npyFiles = {}
    fileList = os.listdir(extractedFolder)
    for filename in fileList:
        if filename.endswith('.gz'):
            f = os.path.join(scriptDirectory, extractedFolder, filename)
            # # npyFiles[filename.strip('.npy.gz')] = gzip.GzipFile(f, 'r')
            # gzFile = gzip.open(f, "rb")
            # unCompressedFile = open(f.strip('.gz'), "wb")
            # decoded = gzFile.read()
            # unCompressedFile.write(decoded)
            # gzFile.close()
            # unCompressedFile.close()
            npyFiles[filename.strip('.npy.gz')] = f.strip('.gz')
            os.system("gzip -dk %s" % f)

    trainImages = np.load(npyFiles['trainImages'], mmap_mode='r')
    trainLabels = np.load(npyFiles['trainLabels'], mmap_mode='r')
    testImages = np.load(npyFiles['testImages'], mmap_mode='r')
    testLabelsIndexes = np.load(npyFiles['testLabels'], mmap_mode='r')
    typeNamesList = np.load(npyFiles['typeNamesList'])
    testTypeNames = np.load(npyFiles['testTypeNames'])
    # testImages = np.load(npyFiles['testImagesNoGal'], mmap_mode='r')
    # testLabelsIndexes = np.load(npyFiles['testLabelsNoGal'], mmap_mode='r')

    print("Completed creatingArrays")
    print(len(trainImages))

    nLabels = len(typeNamesList)

    # Set up the convolutional network architecture
    N = 1024
    imWidth = 32  # Image size and width
    imWidthReduc = 8
    a = []
    x, y_, keep_prob, y_conv = convnet_variables(imWidth, imWidthReduc, N, nLabels)

    with tf.Session() as sess: # config=tf.ConfigProto(inter_op_parallelism_threads=1, intra_op_parallelism_threads=1)) as sess:
        # TRAIN AND EVALUATE MODEL
        cross_entropy = tf.reduce_mean(-tf.reduce_sum(y_ * tf.log(y_conv + 1e-8), reduction_indices=[1]))
        train_step = tf.train.AdamOptimizer(1e-4).minimize(cross_entropy)
        correct_prediction = tf.equal(tf.argmax(y_conv, 1), tf.argmax(y_, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

        sess.run(tf.initialize_all_variables())

        testLabels = labels_indexes_to_arrays(testLabelsIndexes[0:400], nLabels)
        testImages = testImages[0:400]
        # testLabelsWithGal = labels_indexes_to_arrays(testLabelsIndexesWithGal[0:200], nLabels)
        # testImagesWithGal = testImagesWithGal[0:200]

        trainImagesCycle = itertools.cycle(trainImages)
        trainLabelsCycle = itertools.cycle(trainLabels)
        for i in range(400000):
            batch_xs = np.array(list(itertools.islice(trainImagesCycle, 50 * i, 50 * i + 50)))
            batch_ys = labels_indexes_to_arrays(list(itertools.islice(trainLabelsCycle, 50 * i, 50 * i + 50)), nLabels)
            train_step.run(feed_dict={x: batch_xs, y_: batch_ys, keep_prob: 0.5})
            if i % 100 == 0:
                train_accuracy = accuracy.eval(feed_dict={x: batch_xs, y_: batch_ys, keep_prob: 1.0})
                print("step %d, training accuracy %g" % (i, train_accuracy))
                testAcc = accuracy.eval(feed_dict={x: testImages, y_: testLabels, keep_prob: 1.0})
                print("test accuracy %g" % testAcc)
                a.append(testAcc)
                # if i % 1000 == 0:
                #     testWithGalAcc = accuracy.eval(feed_dict={x: testImagesWithGal, y_: testLabelsWithGal, keep_prob: 1.0})
                #     print("test With Gal accuracy %g" % testWithGalAcc)

        print("test accuracy %g" % accuracy.eval(feed_dict={x: testImages, y_: testLabels, keep_prob: 1.0}))

        yy = y_conv.eval(feed_dict={x: testImages, y_: testLabels, keep_prob: 1.0})
        cp = correct_prediction.eval(feed_dict={x: testImages, y_: testLabels, keep_prob: 1.0})
        print(cp)
        for i in range(len(cp)):
            if cp[i] == False:
                predictedIndex = np.argmax(yy[i])
                print(i, testTypeNames[i], typeNamesList[predictedIndex])

        # SAVE THE MODEL
        saveFilename = dataDirName + "tensorflow_model.ckpt"
        saver = tf.train.Saver()
        save_path = saver.save(sess, saveFilename)
        print("Model saved in file: %s" % save_path)

        modelFilenames = [saveFilename + '.index', saveFilename + '.meta', saveFilename + '.data-00000-of-00001']

    # ACTUAL ACCURACY, broadTYPE ACCURACY, AGE ACCURACY
    typeAndAgeCorrect = 0
    typeCorrect = 0
    broadTypeCorrect = 0
    broadTypeAndAgeCorrect = 0
    typeAndNearAgeCorrect = 0
    broadTypeAndNearAgeCorrect = 0
    for i in range(len(testTypeNames)):
        predictedIndex = np.argmax(yy[i])
        testBroadType = testTypeNames[i][0:2]
        actualBroadType = typeNamesList[predictedIndex][0:2]
        if testTypeNames[i][0:3] == 'IIb':
            testBroadType = 'Ib'
        if typeNamesList[predictedIndex][0:3] == 'IIb':
            actualBroadType = 'Ib'
        testType = testTypeNames[i].split(': ')[0]
        actualType = typeNamesList[predictedIndex].split(': ')[0]
        testAge = testTypeNames[i].split(': ')[1]
        actualAge = typeNamesList[predictedIndex].split(': ')[1]
        nearTestAge = testAge.split(' to ')

        if testTypeNames[i] == typeNamesList[predictedIndex]:
            typeAndAgeCorrect += 1
        if testType == actualType:  # correct type
            typeCorrect += 1
            if (nearTestAge[0] in actualAge) or (nearTestAge[1] in actualAge):  # check if the age is in the neigbouring bin
                typeAndNearAgeCorrect += 1  # all correct except nearby bin
        if testBroadType == actualBroadType:  # correct broadtype
            broadTypeCorrect += 1
            if testAge == actualAge:
                broadTypeAndAgeCorrect += 1
            if (nearTestAge[0] in actualAge) or (nearTestAge[1] in actualAge):  # check if the age is in the neigbouring bin
                broadTypeAndNearAgeCorrect += 1  # Broadtype and nearby bin

    typeAndAgeAccuracy = float(typeAndAgeCorrect) / len(testTypeNames)
    typeAccuracy = float(typeCorrect) / len(testTypeNames)
    broadTypeAccuracy = float(broadTypeCorrect) / len(testTypeNames)
    broadTypeAndAgeAccuracy = float(broadTypeAndAgeCorrect) / len(testTypeNames)
    typeAndNearAgeAccuracy = float(typeAndNearAgeCorrect) / len(testTypeNames)
    broadTypeAndNearAgeAccuracy = float(broadTypeAndNearAgeCorrect) / len(testTypeNames)

    print("typeAndAgeAccuracy : " + str(typeAndAgeAccuracy))
    print("typeAccuracy : " + str(typeAccuracy))
    print("broadTypeAccuracy : " + str(broadTypeAccuracy))
    print("broadTypeAndAgeAccuracy: " + str(broadTypeAndAgeAccuracy))
    print("typeAndNearAgeAccuracy : " + str(typeAndNearAgeAccuracy))
    print("broadTypeAndNearAgeAccuracy : " + str(broadTypeAndNearAgeAccuracy))

    return modelFilenames


if __name__ == '__main__':
    t1 = time.time()
    savedFilenames = train_model('data_files/')
    t2 = time.time()
    print("time spent: {0:.2f}".format(t2 - t1))

