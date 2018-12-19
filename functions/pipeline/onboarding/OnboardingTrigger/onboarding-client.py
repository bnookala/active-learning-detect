import requests
import json

print("\nTest client for CLI Onboarding scenario\n-------------------------------------\n")

print("Now executing cURL POST request to onboard images...")

functionURL = "https://mtarngfunc-test.azurewebsites.net/api/onboarding?code=ezQ4rW/DvaNtm6DlHZ7XQp1Enrtao3WpsW4FFR5V/nFLVb9vq4P7PQ=="
headers = {"Content-Type": "application/json"}
urlList = { "imageUrls": ["http://www.whitneyway.com/Images/15/2017%20Puppies%20in%20Easter%20basket%204-16-17_800.JPG",
                         "http://allpetcages.com/wp-content/uploads/2017/06/puppy-whelping-box.jpg",
                         "http://78.media.tumblr.com/eea2f882ec08255e40cecaf8ca1d4543/tumblr_nmxjbjIK141qi4ucgo1_500.jpg"] }

response = requests.post(url = functionURL, headers=headers, json = urlList)

print("Completed cURL POST request.")

raw_response = response.text
response_array = raw_response.split(", ")
response_output = "\n".join(response_array)

print("Response: " + response_output)