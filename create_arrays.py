import numpy as np
import matplotlib.pyplot as plt
from random import shuffle
from sn_processing import PreProcessing


class AgeBinning(object):
    def __init__(self, minAge, maxAge, ageBinSize):
        self.minAge = minAge
        self.maxAge = maxAge
        self.ageBinSize = ageBinSize

    def age_bin(self, age):
        ageBin = int(age / self.ageBinSize) - int(self.minAge / self.ageBinSize)  # around zero has double bin siz

        return ageBin

    def age_labels(self):
        ageLabels = []

        ageBinPrev = 0
        ageLabelMin = self.minAge
        for age in np.arange(self.minAge, self.maxAge):
            ageBin = self.age_bin(age)

            if (ageBin != ageBinPrev):
                ageLabelMax = age
                ageLabels.append(str(ageLabelMin) + " to " + str(ageLabelMax))
                ageLabelMin = ageLabelMax

            ageBinPrev = ageBin

        ageLabels.append(str(ageLabelMin) + " to " + str(self.maxAge))

        return ageLabels


class CreateLabels(object):

    def __init__(self, nTypes, minAge, maxAge, ageBinSize, typeList):
        self.nTypes = nTypes
        self.minAge = minAge
        self.maxAge = maxAge
        self.ageBinSize = ageBinSize
        self.typeList = typeList
        self.ageBinning = AgeBinning(self.minAge, self.maxAge, self.ageBinSize)
        self.numOfAgeBins = self.ageBinning.age_bin(self.maxAge) + 1
        self.nLabels = self.nTypes * self.numOfAgeBins
        self.ageLabels = self.ageBinning.age_labels()       
        

    def label_array(self, ttype, age):
        ageBin = self.ageBinning.age_bin(age)
        labelarray = np.zeros((self.nTypes, self.numOfAgeBins))
        typeNames = []

        try:
            typeIndex = self.typeList.index(ttype)
        except ValueError as err:
            print("INVALID TYPE: {0}".format(err))


        #THIS IS FOR SUPERFIT TEMPLATES - REMOVE THESE IF STATEMENTS LATER
        if (ttype == 'Ia'):
            typeIndex = 0

        elif (ttype == 'Ib'):
            typeIndex = 9

        elif (ttype == 'Ic'):
            typeIndex = 5

        elif (ttype == 'II'):
            typeIndex = 13

        ######################################
            
        labelarray[typeIndex][ageBin] = 1
        labelarray = labelarray.flatten()

        typeNames.append(ttype + ": " + self.ageLabels[ageBin])
        typeNames = np.array(typeNames)

        return labelarray, typeNames


    def type_names_list(self):
        typeNamesList = []
        for tType in self.typeList:
            for ageLabel in self.ageBinning.age_labels():
                typeNamesList.append(tType + ": " + ageLabel)

        return typeNamesList
        


class ReadSpectra(object):

    def __init__(self, w0, w1, nw, z):
        self.w0 = w0
        self.w1 = w1
        self.nw = nw
        self.z = z


    def temp_list(self, tempFileList):
        f = open(tempFileList, 'rU')

        fileList = f.readlines()
        for i in range(0,len(fileList)):
            fileList[i] = fileList[i].strip('\n')

        f.close()

        return fileList

    def snid_template_data(self, snidTemplateLocation, filename, ageIdx):
        """ lnw template files """
        data = PreProcessing(snidTemplateLocation+filename, self.w0, self.w1, self.nw, self.z)
        wave, flux, nCols, ages, tType, minIndex, maxIndex = data.snid_template_data(ageIdx)

        return wave, flux, nCols, ages, tType, minIndex, maxIndex


    def sf_age(self, filename):
        snName, extension = filename.strip('.dat').split('.')
        ttype, snName = snName.split('/')

        if (extension == 'max'):
            age = 0
        elif (extension[0] == 'p'):
            age = float(extension[1:])
        elif (extension[0] == 'm'):
            age = -float(extension[1:])
        else:
            print "Invalid Superfit Filename: " + filename

        return snName, ttype, age


    def superfit_template_data(self, sfTemplateLocation, filename):
        """ Returns wavelength and flux after all preprocessing """
        data = PreProcessing(sfTemplateLocation + filename, self.w0, self.w1, self.nw, self.z)
        wave, flux, minIndex, maxIndex = data.two_column_data()
        snName, ttype, age = self.sf_age(filename)

        print snName, ttype, age

        return wave, flux, minIndex, maxIndex, age, snName, ttype


    def input_spectrum(self, filename):
        data = PreProcessing(filename, self.w0, self.w1, self.nw, self.z)
        wave, flux, minIndex, maxIndex = data.two_column_data()

        return wave, flux, minIndex, maxIndex

class ArrayTools(object):

    def __init__(self, nLabels):
        self.nLabels = nLabels

    def shuffle_arrays(self, images, labels, filenames, typeNames):
        imagesShuf = []
        labelsShuf = []
        filenamesShuf = []
        typeNamesShuf = []

        # Randomise order
        indexShuf = range(len(images))
        shuffle(indexShuf)
        for i in indexShuf:
            imagesShuf.append(images[i])
            labelsShuf.append(labels[i])
            filenamesShuf.append(filenames[i])
            typeNamesShuf.append(typeNames[i])

        return np.array(imagesShuf), np.array(labelsShuf), np.array(filenamesShuf), np.array(typeNamesShuf)


    def count_labels(self, labels):
        counts = np.zeros(self.nLabels)

        for i in range(len(labels)):
            counts = labels[i] + counts

        return counts


    def div0(self, a, b):
        """ ignore / 0, div0( [-1, 0, 1], 0 ) -> [0, 0, 0] """
        with np.errstate(divide='ignore', invalid='ignore'):
            c = np.true_divide(a, b)
            c[~ np.isfinite(c)] = 0  # -inf inf NaN
        return c


    def over_sample_arrays(self, images, labels, filenames, typeNames):
        counts = self.count_labels(labels)
        print "Before OverSample"  #
        print counts  #

        overSampleAmount = self.div0(1 * max(counts), counts)  # ignore zeros in counts
        imagesOverSampled = []
        labelsOverSampled = []
        filenamesOverSampled = []
        typeNamesOverSampled = []

        counts1 = np.zeros(self.nLabels)

        imagesShuf, labelsShuf, filenamesShuf, typeNamesShuf = self.shuffle_arrays(images, labels, filenames, typeNames)

        for i in range(len(labelsShuf)):
            label = labelsShuf[i]
            image = imagesShuf[i]
            filename = filenamesShuf[i]
            typeName = typeNamesShuf[i]

            labelIndex = np.argmax(label)

            for r in range(int(overSampleAmount[labelIndex])):
                imagesOverSampled.append(image)
                labelsOverSampled.append(label)
                filenamesOverSampled.append(filename)
                typeNamesOverSampled.append(typeName)
                counts1 = label + counts1
        print "After OverSample"  #
        print counts1  #

        # [ 372.    8.   22.   12.    1.   22.   26.    6.    1.    7.   34.    5.  44.    6.]
        imagesOverSampled = np.array(imagesOverSampled)
        labelsOverSampled = np.array(labelsOverSampled)
        filenamesOverSampled = np.array(filenamesOverSampled)
        typeNamesOverSampled = np.array(typeNamesOverSampled)
        imagesOverSampledShuf, labelsOverSampledShuf, filenamesOverSampledShuf, typeNamesOverSampledShuf = self.shuffle_arrays(imagesOverSampled, labelsOverSampled, filenamesOverSampled, typeNamesOverSampled)

        return imagesOverSampledShuf, labelsOverSampledShuf, filenamesOverSampledShuf, typeNamesOverSampledShuf


class CreateArrays(object):
    def __init__(self, w0, w1, nw, nTypes, minAge, maxAge, ageBinSize, typeList, z):
        self.w0 = w0
        self.w1 = w1
        self.nw = nw
        self.nTypes = nTypes
        self.minAge = minAge
        self.maxAge = maxAge
        self.ageBinSize = ageBinSize
        self.typeList = typeList
        self.ageBinning = AgeBinning(self.minAge, self.maxAge, self.ageBinSize)
        self.numOfAgeBins = self.ageBinning.age_bin(self.maxAge) + 1
        self.nLabels = self.nTypes * self.numOfAgeBins
        self.z = z
        self.readSpectra = ReadSpectra(self.w0, self.w1, self.nw, self.z)
        self.createLabels = CreateLabels(self.nTypes, self.minAge, self.maxAge, self.ageBinSize, self.typeList)


    def snid_templates_to_arrays(self, snidTemplateLocation, tempfilelist):
        ''' This function is for the SNID processed files, which
            have been preprocessed to negatives, and so cannot be
            imaged yet '''
        templist = self.readSpectra.temp_list(tempfilelist)
        typeList = []
        images = np.empty((0, int(self.nw)), np.float32)  # Number of pixels
        labels = np.empty((0, self.nLabels), float)  # Number of labels (SN types)
        filenames = []
        typeNames = []
        agesList = []

        for i in range(0, len(templist)):
            ncols = 15
            for ageidx in range(0, 100):
                if (ageidx < ncols):
                    tempwave, tempflux, ncols, ages, ttype, tminindex, tmaxindex = self.readSpectra.snid_template_data(snidTemplateLocation, templist[i], ageidx)
                    agesList.append(ages[ageidx])

                    if ((float(ages[ageidx]) > self.minAge and float(ages[ageidx]) < self.maxAge)):
                        label, typeName = self.createLabels.label_array(ttype, ages[ageidx])
                        nonzeroflux = tempflux[tminindex:tmaxindex + 1]
                        newflux = (nonzeroflux - min(nonzeroflux)) / (max(nonzeroflux) - min(nonzeroflux))
                        newflux2 = np.concatenate((tempflux[0:tminindex], newflux, tempflux[tmaxindex + 1:]))
                        images = np.append(images, np.array([newflux2]), axis=0)  # images.append(newflux2)
                        labels = np.append(labels, np.array([label]), axis=0)  # labels.append(ttype)
                        filenames.append(templist[i] + '_' + ttype + '_' + str(ages[ageidx]))
                        typeNames.append(typeName)

            print templist[i]
            # Create List of all SN types
            if ttype not in typeList:
                typeList.append(ttype)

        return typeList, images, labels, np.array(filenames), typeNames

    def superfit_templates_to_arrays(self, sfTemplateLocation, sftempfilelist):
        templist = self.readSpectra.temp_list(sftempfilelist)
        images = np.empty((0, self.nw), np.float32)  # Number of pixels
        labels = np.empty((0, self.nLabels), float)  # Number of labels (SN types)
        filenames = []
        typeNames = []

        for i in range(0, len(templist)):
            tempwave, tempflux, tminindex, tmaxindex, age, snName, ttype = self.readSpectra.superfit_template_data(
                sfTemplateLocation, templist[i])

            if ((float(ages[ageidx]) > minAge and float(ages[ageidx]) > maxAge)):
                label, typeName = label_array(ttype, ages[ageidx])
                nonzeroflux = tempflux[tminindex:tmaxindex + 1]
                newflux = (nonzeroflux - min(nonzeroflux)) / (max(nonzeroflux) - min(nonzeroflux))
                newflux2 = np.concatenate((tempflux[0:tminindex], newflux, tempflux[tmaxindex + 1:]))
                images = np.append(images, np.array([newflux2]), axis=0)  # images.append(newflux2)
                labels = np.append(labels, np.array([label]), axis=0)  # labels.append(ttype)
                filenames.append(templist[i])
                typeNames.append(typeName)

        return images, labels, np.array(filenames), typeNames


