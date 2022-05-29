Greetings :)
This script is used to pull audit events from Lastpass API via rest, written entirely in Python (3.9).

General notes: 
A: The parameters you will need to fill are:
AWS_ACCESS_KEY_ID = user/role that pulls the logs from the server to S3.
AWS_SECRET_ACCESS_KEY = same
BUCKET_NAME = "" #bucket name to upload jsons to. will automatically create a folder inside this bucket called "lastpass-auditlogs"
(if you don't want that to occur just remove from func "upload_to_s3".
LASTPASS_API_KEY
LASTPASS_API_URL = at the time of script creation, this was  "https://lastpass.com/enterpriseapi.php". if changes, adjust accordingly.
LOCAL_DIRECTORY = if you run this locally, just leave blank. if you put this on a server with cronjob, you need to state the directory where you put the script in your server.

B: The script creates a local file called "lastpass_last_event_time.txt" where it saves the last time of event occurance, and ofc reads it next time script is ran.
C: at the time of the file creation, Lastpass request parameter: [data][from] did not work well, so all requests return all events from 00:00 same day by default.
   to overcome this the script removes irrelevnt events based on the value in the "latpass_last_event_time.txt.
