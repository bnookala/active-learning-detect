import os
import logging
import azure.functions as func
from shutil import copyfile
from ...shared import db_access as DB_Access

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
        logging.error(req.get_json())
        url_list = req_body["imageUrls"]
        url_string = (", ".join(url_list))
    except ValueError:
        print("Unable to decode JSON body")
        return func.HttpResponse("Unable to decode POST body", status_code=400)

    logging.error(req_body)

    # Verbose output of HttpResponse, for testing
    return func.HttpResponse("Got body\n\nURL List:\n" + url_string, status_code=200)

    # Build list of image objects to pass to DAL for insertion into DB.
    image_object_list = []

    for url in url_list:
        # Split original image name from URL
        original_filename = url.split("/")[-1]

        # Create ImageInfo object (def in db_access.py)
        # Note: For testing, default image height/width are set to 50x50
        image = DB_Access.ImageInfo(original_filename, url, 50, 50)

        # Append image object to the list
        image_object_list.append(image)

    # Connect to DB
    db = DB_Access.get_connection()

    # Hand off list of image objects to DAL to create rows in database
    # Receive dictionary of mapped { ImageID : ImageURL }
    image_id_url_map = DB_Access.get_image_ids_for_new_images(db, image_object_list)

    # Copy over images to permanent blob store, get list of URLs to iamges in permanent storage
    # Iterating over a dictionary in Python: https://stackoverflow.com/questions/3294889/iterating-over-dictionaries-using-for-loops
    # Syntax for copying a file in Python: copyfile(src, dst)
    # TODO: Figure out how to parse final filename: https://stackoverflow.com/questions/26443308/find-last-occurrence-of-character-in-string-python
    for key, value in image_id_url_map.items():
        file_extension = os.path.splitext(value)[1]
        permanent_storage_directory = "some_storage_url"
        permanent_storage_path = permanent_storage_directory + "/" + key + file_extension
        copyfile(value, permanent_storage_path)

    # Close connection to database.
    db.close()