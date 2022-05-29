import requests
import xmltodict
import json
from datetime import datetime
import boto3

AWS_ACCESS_KEY_ID = "" #for the user/role that pulls the logs from the server to S3.
AWS_SECRET_ACCESS_KEY = ""
BUCKET_NAME = "" #bucket name to upload jsons to
LASTPASS_API_KEY = ""
LASTPASS_API_URL = "https://lastpass.com/enterpriseapi.php"
LOCAL_DIRECTORY = "" #directory where you put the script in your server.
filename = "" #set by the create_json_file function -leave empty
file_name = "" #value for file name to be created. changed in the "create_file_with_relevant_alerts" function -leave empty
last_event_timestampstring = "" # -leave empty
relevent_events_dict = {} #dict to store relevant events (see "create_file_with_relevant_alerts" description for details"
HEADERS = {'Content-type': 'application/json',
           }
PARAMS = {"cid": "19702041",
        "provhash": f"{LASTPASS_API_KEY}",
        "cmd": "reporting"}


def lastpass_logs_request(url,headers,params):
    """
performs request to the lastpass api for "reporting" events.
    :param url: lastpass api URL
    :param headers: request headers
    :param params: parameters to be passed in the request
    :return: response text
    """
    try:
        res = requests.post(url,headers=headers,params=params)
        return True, res.text
    except Exception as e:
        return False, "An error occured during the initial request from Lastpass API:" + str(e)


def convert_xml_to_json(xml_content):
    """
    converts xml response to json object
    :param xml_content: xml content receieved from the lastpass request
    :return: request of the json object
    """
    try:
        json_object = xmltodict.parse(xml_content)
        return True, json_object
    except Exception as e:
        return False, "failed to convert xml to json:" + str(e)


def upload_to_s3(event_file_name, f_bucket_name=BUCKET_NAME): #<----
    """
    opens up a session to aws and upload the updated json file to the s3 bucket specified
    :param f_bucket_name: bucket name
    :param event_file_name: name of the event file to be uploaded to s3
    :return: None
    """
    try:
        session = boto3.Session(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        s3 = session.resource("s3")
        s3.meta.client.upload_file(f"/home/freshdesk/AutomatedChecks/Lastpass_to_s3/{event_file_name}", f_bucket_name, "lastpass-auditlogs/" + file_name)

    except Exception as e:
        "failed to upload file to the s3 bucket:" + str(e)


def pull_last_event_time_captured_from_dict():
    """
    pulls the last event time of the updated dict.
    :return: last event time from updated dict.
    """
    global file_name
    try:
        with open(f"{LOCAL_DIRECTORY}/{file_name}", "r") as f_content:
            f_content_json = json.load(f_content)
            last_event_time = f_content_json["Event1"]["@Time"]
            return last_event_time
    except Exception as e:
        return False, "Failed to pull last event time from dict" + str(e)


def insert_last_event_time_to_file():
    """
    inserts the last event time from updated dict to the "lsatpass_last_event_time.txt which serves the script for the
    next time it runs.
    :return: None.
    """
    global relevent_events_dict
    try:
        last_event_time= relevent_events_dict["Event1"]["@Time"]
        with open(f"{LOCAL_DIRECTORY}/lastpass_last_event_time.txt", "w") as f:
            f.write(last_event_time)
    except Exception as e:
        return False, "Failed to insert last event time to file" + str(e)


def retrieve_last_event_timestamp_from_log_file():
    """
    retrieves the last event timestamp captured from last time the script ran. if the file is empty, it inserts the
    time when the script ran.
    :return: if empty, current time. if was with value, the last event of the previous time the script ran.
    """
    #try:
    with open(f"{LOCAL_DIRECTORY}/lastpass_last_event_time.txt", "r+") as f_content:
        timestamp_string = str(f_content.read())
        if len(timestamp_string) == 0:
            now = datetime.now()
            now_date_strfed = str(now.strftime("%Y-%m-%d %H:%M:%S"))
            f_content.write(now_date_strfed)
            return now_date_strfed, "file was empty, added default value",
        else:
            return timestamp_string, "added value from timestamp file",
    #except Exception as e:
        #return False, "Failed to retrieve timestamp from file" + str(e)


def add_timestamp_to_params(parameters, timestamp_from_file):
    """
    inserts the last event timestamp to the parameters passed in the request to the lastpass api.
    *currently lastpass api does not support the "from" parameter that is in their documentations. CLOWNS. so the
    "create_file_with_relevant_alerts" function performs it locally.
    :param parameters: request parameters
    :param timestamp_from_file: last event timestamp from file
    :return: updated parameters with the last event timestamp
    """
    now = datetime.now()
    now_date = str(now.strftime("%Y-%m-%d %H:%M:%S"))
    parameters["data"] = {"from": timestamp_from_file, "to": now_date}
    return parameters


def create_file_with_relevant_alerts(json_object, timestamp_from_last_event_file):
    """
    creates a json file with alerts that came after the last event time as captured in the "lastpass+last_event_time.txt"
    :param json_object: json object with all of the alerts recieved from the lastpass api
    :param timestamp_from_last_event_file: timestamp from the lastpass_last_event_time.txt
    :return: None. creates the file to be uploaded.
    """
    global file_name
    global relevent_events_dict
    date = datetime.now()
    now_date_string = date.strftime("%Y-%m-%d %H:%M:%S") #for file name
    file_name = f"lastpasslogs | {now_date_string}.json"
    last_event_datetime_object = datetime.strptime(timestamp_from_last_event_file,"%Y-%m-%d %H:%M:%S")
    with open (f"{LOCAL_DIRECTORY}/{file_name}","w") as f_content:
        for value in json_object.values():
            for deeper_key, deeper_value in value.items():
                try:
                    temp_log_time_from_event = datetime.strptime(deeper_value["@Time"],"%Y-%m-%d %H:%M:%S")
                    if last_event_datetime_object < temp_log_time_from_event:
                        relevent_events_dict[deeper_key] = deeper_value
                    else:
                        pass
                except:
                    pass
        f_content.write(json.dumps(relevent_events_dict))
        return file_name


def read_json_per_event_and_upload_to_s3(created_alert_file):
    """
    opens up the json file with relevant alerts and create json file for each alert, and uploads them to s3.
    :param created_alert_file: the file with relevant alerts.
    :param local_count: used to create different names for each json file created
    :return: None. uploads the single event files
    """
    global file_name
    local_count = 0
    date = datetime.now()
    now_date_string = date.strftime("%Y-%m-%d %H:%M:%S")  # for file name
    with open(f"{LOCAL_DIRECTORY}/{file_name}",'r') as file_content:
        json_dict = json.loads(file_content.read())
        print(json_dict)
    for event in json_dict.values():
        temp_file_event_name = f"lastpass_event {local_count} | {now_date_string}.json"
        with open(f"{LOCAL_DIRECTORY}/{temp_file_event_name}", "w") as event_content:
            event_content.write(json.dumps(event))
        upload_to_s3(f"{LOCAL_DIRECTORY}/{temp_file_event_name}")
        local_count += 1


def main():
    global last_event_timestampstring
    last_event_timestampstring, output_timestamp = retrieve_last_event_timestamp_from_log_file()
    if last_event_timestampstring:
        add_timestamp_to_params(PARAMS, last_event_timestampstring)
    success, xml_response_text = lastpass_logs_request(LASTPASS_API_URL, HEADERS, PARAMS)
    if success:
        json_creation_sucess, json_object_with_all_alerts = convert_xml_to_json(xml_response_text)
        json_file_name = create_file_with_relevant_alerts(json_object_with_all_alerts, last_event_timestampstring)
        read_json_per_event_and_upload_to_s3(json_file_name)
        insert_last_event_time_to_file()
    else:
        return


if __name__ == "__main__":
    main()