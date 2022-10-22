from flask import Flask, render_template
import os
app = Flask(__name__, static_folder="")
import datetime
import random

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/fetchFiles", methods=['GET'])
def droneFiles():
    print("droneFiles Was Called!")
    global inputBucket
    inputBucket = "InputBucket" + str(datetime.datetime.now().timestamp())
    print(str(datetime.datetime.now().timestamp()))
    global outputBucket
    outputBucket = "OutputBucket" + str(datetime.datetime.now().timestamp())
    createBucket(inputBucket)
    createBucket(outputBucket)
    global outputBucketPreAuthUri
    global inputBucketPreAuthUri
    global inputBucketParId
    global outputBucketParId
    inputBucketPreAuthUri, inputBucketParId = createPreAuthRequest(inputBucket)
    outputBucketPreAuthUri, outputBucketParId = createPreAuthRequest(outputBucket)
    curDir = os.getcwd()
    dirToWriteForFlask = curDir + "/images/"
    # Temporary comment out for manual files.  Remove when working with drone files
    files = fetchFile(dirToWriteForFlask, inputBucketPreAuthUri)
    # print(files)
    #files = ["s1014849"]  #Temporary array for static files
    return render_template('fetchFiles.html', imageFileList = files)

@app.route("/drawBoxes", methods=['GET'])
def displayBoundingBoxes():
    print("drawBoxes Was Called!")
    curDir = os.getcwd()
    dirToWriteForFlask = curDir + "/images/"
    visionML()
    files = drawBox(dirToWriteForFlask)
    updateFusion()
    return render_template('displayBoundingBoxes.html', imageFileList = files, pipeCount = pipeInventoryCount)

@app.route("/demoComplete", methods=['GET'])
def finishDemo():
    deleteParId(inputBucket, inputBucketParId)
    deleteParId(outputBucket, outputBucketParId)
    objectsToDelete = listObjects(inputBucket)
    deleteObjects(objectsToDelete, inputBucket)
    objectsToDelete = listObjects(outputBucket)
    deleteObjects(objectsToDelete, outputBucket)
    deleteBucket(inputBucket)
    deleteBucket(outputBucket)
    return render_template('index.html')


def updateFusion():
    import requests
    import json
    from requests.auth import HTTPBasicAuth

    fusionUrl = "https://fa-eyjt-fusionappsqa.fa.ocs.oc-test.com/fscmRestApi/resources/11.13.18.05/cycleCountSequenceDetails"
    user = "Jim.Smith"
    password = "uhU5s1e)dqyr"
    payload = json.dumps({
        'CycleCountName': 'Zone 21',
        'OrganizationCode': 'IM102MFG',
        'ItemNumber': 'ST7520',
        'Subinventory': 'Stores',
        'CountQuantity': pipeInventoryCount,
        'CountUOMCode': 'Ea',
        'ProcessingFlag': True,
        'Comments': 'Counting done'
    })

    headers = {
        'Content-Type': 'application/json'
    }

    auth = HTTPBasicAuth(user, password)

    response = requests.request("POST", fusionUrl, headers=headers, data=payload, auth=auth)
    print("Wrote to Fusion...")
    print(response.text)
    print(response.status_code)

def drawBox(dirToWriteForFlask):
    import requests
    import json
    import cv2


    ociObjectUrlInput = "https://objectstorage.us-ashburn-1.oraclecloud.com/p/7CcLR7ovFSchSgJ2BelkPBZY-qu3Q0NFFN1OeYOsD1_W5da5PjdyN-OkdklVcK48/n/ociobenablement/b/test/o/"
    ociObjectUrlOutput = "https://objectstorage.us-ashburn-1.oraclecloud.com" + outputBucketPreAuthUri
    # ociObjectUrlOutput = "https://objectstorage.us-ashburn-1.oraclecloud.com/p/ztX01S2kAuv9DRnuCeng3_q5PzPVNXK0mCzNGOr0nlJRai_ZAP6GRMdJom_ZFx0s/n/ociobenablement/b/test_output/o/"
    objectBoundingCoordinates = []
    images = []
    #mediaFilesUuid = ["s1014849"] #temporarily set this variable.  This should be removed

    response = requests.request("GET", ociObjectUrlOutput)
    data = json.loads(response.text)

    global mediaFilesUuid

    print("OUTPUT FROM REST CALL")
    print(data)

    boundingBoxFiles = []
    objects = data["objects"]
    print("OBJECTS:")
    print(objects)
    for object in objects:
        if job_id in object["name"] and "json" in object["name"]:
            response = requests.request("GET", ociObjectUrlOutput+object["name"])
            data = json.loads(response.text)
            imageObjects = data["imageObjects"]
            pipeDimensions = []
            for item in imageObjects:
                if item['confidence'] > 0.50 :
                    boundingPolygon = item["boundingPolygon"]
                    normalizedVertices = boundingPolygon["normalizedVertices"]
                    pipeDimensions.append(normalizedVertices)

            str = object["name"].split("_")
            print(len(str))
            image = str[2].split(".json")[0].split(".jpg")[0]

            img = cv2.imread(dirToWriteForFlask+image+"_cropped.jpg") #inserted _cropped
            img_orig = cv2.imread(dirToWriteForFlask+image+".jpg")
            imgCopy = img.copy()
            imgY = imgCopy.shape[0]
            imgX = imgCopy.shape[1]
            print("Pipe Dimensions Length")
            print(pipeDimensions)

            for pipe in pipeDimensions:
                pipeCoordsMin = pipe[0]
                pipeCoordsMax = pipe[2]
                pipeMinX = int(pipeCoordsMin["x"] * imgX)
                pipeMinY = int(pipeCoordsMin["y"] * imgY)
                pipeMaxX = int(pipeCoordsMax["x"] * imgX)
                pipeMaxY = int(pipeCoordsMax["y"] * imgY)
                cv2.rectangle(imgCopy, (pipeMinX, pipeMinY), (pipeMaxX, pipeMaxY), (0, 0, 255), 5)

            cv2.imwrite(dirToWriteForFlask+image+"_CroppedBoundingBoxes.jpg", imgCopy) #imgCopy)

            # insert the cropped image back in the original image, imgCopy has the bounding boxes drawn
            img_orig[cropPositions["startX"]:cropPositions["endX"],
                cropPositions["startY"]:cropPositions["endY"]] = imgCopy

            cv2.imwrite(dirToWriteForFlask+image+"_boundingBoxes.jpg", img_orig) #imgCopy)
            boundingBoxFiles.append(image+"_boundingBoxes")

    return boundingBoxFiles


def fetchFile(dirToWriteForFlask, inputBucketUri):
    import requests
    import json
    import cv2

    flightUrl = "http://api.skydio.com/api/v0/flights"
    mediaUrl = "http://api.skydio.com/api/v0/media_files"
    downloadUrl = "http://api.skydio.com/api/v0/media/download"
    ociObjectUrl = "https://objectstorage.us-ashburn-1.oraclecloud.com" + inputBucketUri
    # ociObjectUrl = "https://objectstorage.us-ashburn-1.oraclecloud.com/p/7CcLR7ovFSchSgJ2BelkPBZY-qu3Q0NFFN1OeYOsD1_W5da5PjdyN-OkdklVcK48/n/ociobenablement/b/test/o/"

    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': 'dece521ad09dad2060808d44ba490358914db737c2cbfdc8c9b5b9793107ed70'
    }

    response = requests.request("GET", flightUrl, headers=headers, data=payload)

    flights = []
    data = json.loads(response.text)
    for key, value in data.items():
        if key == "data":
            newData = value
            for key, value in newData.items():
                if key == "flights":
                    for i in value:
                        if i["has_telemetry"] == True:
                            flights.append(i["flight_id"])

    # Create list of image uuid's from latest flight that has images
    global mediaFilesUuid
    global cropPositions
    for flightId in flights:
        mediaFilesUuid = []
        url = mediaUrl+"?per_page=25&page_number=1&kind=vehicleImage&flight_id="+flightId
        response = requests.request("GET", url, headers=headers, data=payload)
        data = json.loads(response.text)
        newData = data["data"]
        newDataFiles = newData["files"]
        for i in newDataFiles:
            mediaFilesUuid.append(i["uuid"])
        if len(mediaFilesUuid) != 0:
            break
    else:
        print("error retrieving flight id")

    cropPositions = {}
    # below start and end point ratios were taken from Photoshop
    # the size shown in Photoshop did not reflect the size in cv2 hence I adopted the ratios 
    rStartY = 0.30
    rEndY = 0.65
    rStartX = 0.1
    rEndX = 0.65

    #looking little down
    #rStartY = 4212/56304 
    #rEndY = 33697/56304
    #rStartX = 16896/42219
    #rEndX = 36219/42219

    sizeX = 3040
    sizeY = 4056
    # Cropping an image
    cropPositions["startX"] = int(sizeX*rStartX)
    cropPositions["endX"] = int(sizeX*rEndX)
    cropPositions["startY"] = int(sizeY*rStartY)
    cropPositions["endY"] = int(sizeY*rEndY)

    for uuid in mediaFilesUuid:
        print("Media UUID is")
        print(uuid)
        cropPositions[uuid] = {}
    # Read images from drone
        downloadUrlWithUuid = downloadUrl+"/"+uuid
        fileResponse = requests.request("GET", downloadUrlWithUuid, headers=headers, data=payload)
        fileToWrite = fileResponse.content

    # Write file locally for flask server
        fileNamePath = dirToWriteForFlask+uuid+".jpg"
        file = open(fileNamePath, 'wb')
        file.write(fileToWrite)
        file.close()
        print("wrote file locally...")

    #crop images
    #now crop the image file at the desired location
        print("Cropping images")
        img = cv2.imread(fileNamePath)
        print(img.shape) # Print image shape
        sizeX = img.shape[0]
        sizeY = img.shape[1]

        cropped_image = img[cropPositions["startX"]:cropPositions["endX"],
            cropPositions["startY"]:cropPositions["endY"] ]

        croppedFileNamePath = dirToWriteForFlask+uuid+"_cropped.jpg"
        cv2.imwrite(croppedFileNamePath, cropped_image)
        print("Saved cropped image")
    
    # Write drone images to OCI object storage
        print("Writing image to object store")
        croppedFile = open(croppedFileNamePath, 'rb')
        croppedFileContent = croppedFile.read()
        croppedFile.close()
        objectUrl = ociObjectUrl+uuid+".jpg"
        objectResponse = requests.request("PUT", objectUrl, headers=headers, data=croppedFileContent) #fileToWrite)
        print("object storage return status")
        print(objectResponse.status_code)


    return mediaFilesUuid


def visionML():

    import json
    import oci
    import time
    from vision_service_python_client.ai_service_vision_client import AIServiceVisionClient
    from vision_service_python_client.ai_service_vision_client import AIServiceVisionClient
    from vision_service_python_client.models.inline_image_details import InlineImageDetails
    from vision_service_python_client.models.analyze_image_details import AnalyzeImageDetails
    from vision_service_python_client.models.object_storage_image_details import ObjectStorageImageDetails
    from vision_service_python_client.models.image_classification_feature import ImageClassificationFeature
    from vision_service_python_client.models.image_object_detection_feature import ImageObjectDetectionFeature
    from vision_service_python_client.models.image_text_detection_feature import ImageTextDetectionFeature
    from vision_service_python_client.ai_service_vision_client import AIServiceVisionClient
    from vision_service_python_client.models.create_image_job_details import CreateImageJobDetails
    from vision_service_python_client.models.image_classification_feature import ImageClassificationFeature
    from vision_service_python_client.models.image_object_detection_feature import ImageObjectDetectionFeature
    from vision_service_python_client.models.image_text_detection_feature import ImageTextDetectionFeature
    from vision_service_python_client.models.input_location import InputLocation
    from vision_service_python_client.models.object_list_inline_input_location import ObjectListInlineInputLocation
    from vision_service_python_client.models.object_location import ObjectLocation
    from vision_service_python_client.models.object_storage_document_details import ObjectStorageDocumentDetails
    from vision_service_python_client.models.output_location import OutputLocation
    from vision_service_python_client.models.object_list_inline_input_location import ObjectListInlineInputLocation

    config = oci.config.from_file('~/.oci/config')

    endpoint = "https://vision.aiservice.us-ashburn-1.oci.oraclecloud.com"
    object_detection_modelid = "ocid1.aivisionmodel.oc1.iad.amaaaaaanlc5nbyadmo4j3md7t4shu5yjg77y5zcadnnya3psje46yowzuca"
    namespace = "ociobenablement"
    # input_bucket = "test"
    # output_bucket = "test_output"
    input_bucket = inputBucket
    output_bucket = outputBucket
    compartment = "ocid1.compartment.oc1..aaaaaaaaj7pgqygsuco2f54crotdyheuqsv6gvpphpfrdvge5gnraeoyd2ka"
    start_image = mediaFilesUuid[0] + ".jpg" #this should work set as this: mediaFilesUuid[0]
    MAX_RESULTS = 50

    # Initialize client service_endpoint is optional if it's specified in config
    # ai_service_vision_client = AIServiceVisionClient(config=config, service_endpoint=endpoint)
    ai_service_vision_client = AIServiceVisionClient(config=config)
    object_storage_client = oci.object_storage.ObjectStorageClient(config)

    # Set up request body with multiple features
    # image_classification_feature = ImageClassificationFeature()
    # image_classification_feature.max_results = MAX_RESULTS
    image_object_detection_feature = ImageObjectDetectionFeature()
    image_object_detection_feature.max_results = MAX_RESULTS
    image_object_detection_feature.model_id = object_detection_modelid
    # image_text_detection_feature = ImageTextDetectionFeature()
    features = [image_object_detection_feature]

    # Set up list of images
    list_objects_response = object_storage_client.list_objects(
        namespace_name=namespace,
        bucket_name=input_bucket)

    testdata = list_objects_response.data.objects
    # Setup input locations
    j = 0  # set index
    object_locations = []  # initialize list
    for i in testdata:
        object_locations.append(ObjectLocation())
        object_locations[j].namespace_name = namespace
        object_locations[j].bucket_name = input_bucket
        object_locations[j].object_name = i.name
        j = j + 1
    # object_locations = [object_location]
    input_location = ObjectListInlineInputLocation()
    input_location.object_locations = object_locations

    # Setup output location
    output_location = OutputLocation()
    output_location.namespace_name = namespace
    output_location.bucket_name = output_bucket
    output_location.prefix = "result"

    # Details setup
    create_image_job_details = CreateImageJobDetails()
    create_image_job_details.features = features
    create_image_job_details.compartment_id = "ocid1.compartment.oc1..aaaaaaaaj7pgqygsuco2f54crotdyheuqsv6gvpphpfrdvge5gnraeoyd2ka"
    create_image_job_details.output_location = output_location
    create_image_job_details.input_location = input_location

    res = ai_service_vision_client.create_image_job(create_image_job_details=create_image_job_details)
    print("**************************Analyze Image Batch Job**************************")
    print(res.data)

    global job_id
    job_id = res.data.id
    print(job_id)
    seconds = 0
    res = ai_service_vision_client.get_image_job(image_job_id=job_id)
    while res.data.lifecycle_state == "IN_PROGRESS" or res.data.lifecycle_state == "ACCEPTED":
        print("Job " + job_id + " is IN_PROGRESS for " + str(seconds) + " seconds")
        time.sleep(5)
        seconds += 5
        res = ai_service_vision_client.get_image_job(image_job_id=job_id)

    print("**************************Get Image Job Result**************************")
    print(res.data)

    list_objects_response = object_storage_client.list_objects(
        namespace_name=namespace,
        bucket_name=output_bucket,
        start="result/" + job_id + "/" + namespace + "_" + input_bucket + "_" + start_image + ".json")


    global pipeInventoryCount
    # Test type of object
    list_results_names = (list_objects_response.data.objects)
    print("List Results Names:")
    print(list_results_names)
    print("Final ML Loop Image Count:")
    print(range(len(list_results_names)))
    for i in range(len(list_results_names)):  # subtract 5 to delete the non-interested .json files - this may vary
        pipes_count_i = 0

        if job_id in list_objects_response.data.objects[i].name:
            object_text = object_storage_client.get_object(
                namespace_name=namespace,
                bucket_name=output_bucket,
                object_name=list_objects_response.data.objects[i].name)

            dict_value = json.loads(object_text.data.content)
            print(list_objects_response.data.objects[i].name)
            for pipes in dict_value['imageObjects']:
                if pipes['confidence'] >= 0.50:
                    if pipes['name'] == 'pipes':
                        pipes_count_i += 1

            print(pipes_count_i)
            pipeInventoryCount = pipes_count_i

def createBucket(bucketName):
    import oci
    config = oci.config.from_file('~/.oci/config')
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    namespace = "ociobenablement"
    # bucketName = "innovationLabTest"

    create_bucket_response = object_storage_client.create_bucket(
        namespace_name=namespace,
        create_bucket_details=oci.object_storage.models.CreateBucketDetails(
        name=bucketName,
        compartment_id="ocid1.compartment.oc1..aaaaaaaaj7pgqygsuco2f54crotdyheuqsv6gvpphpfrdvge5gnraeoyd2ka",
        public_access_type="ObjectRead",
        storage_tier="Standard",
        object_events_enabled=False,
        versioning="Disabled",
        auto_tiering="Disabled"))

    print(create_bucket_response.data)

def deleteBucket(bucketName):
    import oci
    config = oci.config.from_file('~/PycharmProjects/visionDemo/.oci/config')
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    namespace = "ociobenablement"
    # bucketName = "innovationLabTest"

    delete_bucket_response = object_storage_client.delete_bucket(
    namespace_name=namespace,
    bucket_name=bucketName)

def createPreAuthRequest(bucketName):
    import oci
    from datetime import datetime
    import json
    config = oci.config.from_file('~/.oci/config')
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    namespace = "ociobenablement"
    # bucketName = "innovationLabTest"

    create_preauthenticated_request_response = object_storage_client.create_preauthenticated_request(
    namespace_name=namespace,
    bucket_name=bucketName,
    create_preauthenticated_request_details=oci.object_storage.models.CreatePreauthenticatedRequestDetails(
        name="samplePreAuthRequest",
        access_type="AnyObjectReadWrite",
        time_expires=datetime.strptime(
            "2023-03-21T15:52:36.708Z",
            "%Y-%m-%dT%H:%M:%S.%fZ"),
        bucket_listing_action="ListObjects"))

    response = json.loads(str(create_preauthenticated_request_response.data))
    print(response)
    preAuthUri = response["access_uri"]
    par_Id = response["id"]
    print("Par ID")
    print(par_Id)
    return preAuthUri, par_Id

def deleteParId(bucketName, parId):
    import oci
    config = oci.config.from_file('~/.oci/config')
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    namespace = "ociobenablement"
    # bucketName = "innovationLabTest"

    delete_preauthenticated_request_response = object_storage_client.delete_preauthenticated_request(
        namespace_name=namespace,
        bucket_name=bucketName,
        par_id=parId)

def listObjects(bucketName):
    import oci
    import json
    config = oci.config.from_file('~/.oci/config')
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    namespace = "ociobenablement"
    # bucketName = "test_output"

    list_objects_response = object_storage_client.list_objects(
        namespace_name=namespace,
        bucket_name=bucketName,
        limit=165)

    # Get the data from response
    print(list_objects_response.data)

    objectsToDelete = []
    result = json.loads(str(list_objects_response.data))
    objects = result["objects"]
    for object in objects:
        objectsToDelete.append(object["name"])

    return objectsToDelete
    # print("objects to delete")
    # print(objectsToDelete)

def deleteObjects(objects, bucketName):
    import oci

    config = oci.config.from_file('~/.oci/config')
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    namespace = "ociobenablement"

    for objectName in objects:
        delete_object_response = object_storage_client.delete_object(
            namespace_name=namespace,
            bucket_name=bucketName,
            object_name=objectName)

if __name__ == '__main__':
    mediaFilesUuid = []
    app.run(host='localhost', port=5000, use_reloader=False)


