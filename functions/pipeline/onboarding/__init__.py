import os
import logging
import json
import azure.functions as func

from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageInfo
from azure.storage.blob import BlockBlobService

# TODO: User id as param to function - holding off until further discussion
# regarding whether user ID should be generated/looked up by the CLI or
# from within this function

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    user_name = req.params.get('userName')

    if not user_name:
        return func.HttpResponse(
            status_code=401,
            headers={ "content-type": "application/json"},
            body=json.dumps({"error": "invalid userName given or omitted"})
        )

    try:
        req_body = req.get_json()
        logging.error(req.get_json())
        raw_url_list = req_body["imageUrls"]
    except ValueError:
        print("Unable to decode JSON body")
        return func.HttpResponse("Unable to decode POST body", status_code=400)

    logging.error(req_body)

    # Build list of image objects to pass to DAL for insertion into DB.
    image_object_list = []
    image_name_list = []
    
    # Check to ensure image URLs sent by client are all unique.
    url_list = set(raw_url_list)

    # TODO: Encapsulate this loop in a method
    # TODO: Wrap method in try/catch, send an appropriate http response in the event of an error
    for url in url_list:
        # Split original image name from URL
        original_filename = url.split("/")[-1]
        image_name_list.append(original_filename)
        # Create ImageInfo object (def in db_access.py)
        # Note: For testing, default image height/width are set to 50x50
        # TODO: Figure out where actual height/width need to come from
        image = ImageInfo(original_filename, url, 50, 50)
        # Append image object to the list
        image_object_list.append(image)

    # TODO: Wrap db access section in try/catch, send an appropriate http response in the event of an error
    data_access = ImageTagDataAccess(get_postgres_provider())
    user_id = data_access.create_user(user_name)

    # Add new images to the database, and retrieve a dictionary ImageId's mapped to ImageUrl's
    image_id_url_map = data_access.add_new_images(image_object_list,user_id)

    # Print out dictionary for debugging
    logging.info("Image ID and URL map dictionary:")
    logging.info(image_id_url_map)

    # Copy over images to permanent blob store and save URLs in a list
    permanent_url_list = []
    update_urls_dictionary = {}

    # TODO: Add check to make sure image exists in temp storage before attempting these operations
    # TODO: Put blob storage manipulation into a separate function and add to shared codebase
    # TODO: Try/catch to distinguish among errors
    for key, value in image_id_url_map.items():

        # Verbose logging for testing
        logging.info("Key: " + key)
        logging.info("Value: " + str(value))

        original_image_url = key
        original_blob_name = original_image_url.split("/")[-1]
        file_extension = os.path.splitext(original_image_url)[1]
        image_id = value
        new_blob_name = (str(image_id) + file_extension)
        copy_from_container = os.getenv('SOURCE_CONTAINER_NAME')
        copy_to_container = os.getenv('DESTINATION_CONTAINER_NAME')
        permanent_storage_path = "https://{0}.blob.core.windows.net/{0}/{1}".format(copy_from_container, new_blob_name)

        # Verbose logging for testing
        logging.info("Original image URL: " + original_image_url)
        logging.info("Original image name: " + original_blob_name)
        logging.info("File extension: " + file_extension)
        logging.info("Image ID: " + str(image_id))
        logging.info("New blob name: " + new_blob_name)
        logging.info("Now copying file from temporary to permanent storage...")
        logging.info("Permanent image URL: " + permanent_storage_path)

        blob_service = BlockBlobService(account_name=os.getenv('STORAGE_ACCOUNT_NAME'), account_key=os.getenv('STORAGE_ACCOUNT_KEY'))
        source_blob_url = blob_service.make_blob_url(copy_from_container, original_blob_name)

        # TODO: Exception handling in case blob cannot be copied for some reason.
        blob_service.copy_blob(copy_to_container, new_blob_name, source_blob_url)
        logging.info("Done.")

        # Delete the file from temp storage once it's been copied
        # Note: The following delete code works.  Commenting out for testing of other functions.
        '''
        logging.info("Now deleting image " + original_blob_name + " from temp storage container.")
        try:
            blob_service.delete_blob(copy_from_container, original_blob_name)
            print("Blob " + original_blob_name + " has been deleted successfully")
        except:
            print("Blob " + original_blob_name + " deletion failed")
        '''

        # Add image to the list of images to be returned in the response
        permanent_url_list.append(permanent_storage_path)
        # Add ImageId and permanent storage url to new dictionary to be sent to update function
        update_urls_dictionary[image_id] = permanent_storage_path

    logging.info("Now updating permanent URLs in the DB...")
    data_access.update_image_urls(update_urls_dictionary, user_id)
    logging.info("Done.")

    # Construct response string of permanent URLs
    permanent_url_string = (", ".join(permanent_url_list))

    # Return string containing list of URLs to images in permanent blob storage
    return func.HttpResponse("The following images should now be added to the DB and exist in permanent blob storage: \n" 
        + permanent_url_string, status_code=200)
