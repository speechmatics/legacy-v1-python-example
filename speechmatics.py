"""
Example script for integrating with the Speechmatics API
"""

import codecs
import json
import logging
import time
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import requests


class SpeechmaticsError(Exception):
    """
    For errors that are specific to Speechmatics systems and pipelines.
    """

    def __init__(self, msg, returncode=1):
        super(SpeechmaticsError, self).__init__(msg)
        self.msg = msg
        self.returncode = returncode

    def __str__(self):
        return self.msg


class SpeechmaticsClient(object):
    """
    A simple client to interact with the Speechmatics REST API
    Documentation at https://app.speechmatics.com/api-details
    """

    def __init__(self, api_user_id, api_token, base_url='https://api.speechmatics.com/v1.0'):
        self.api_user_id = api_user_id
        self.api_token = api_token
        self.base_url = base_url

    def job_post(self, opts):
        """
        Upload a new audio file to speechmatics for transcription
        If text file is specified upload that as well for an alignment job
        If upload suceeds then this method will return the id of the new job

        If succesful returns an integer representing the job id
        """

        url = "".join([self.base_url, '/user/', self.api_user_id, '/jobs/'])
        params = {'auth_token': self.api_token}
        try:
            files = {'data_file': open(opts.audio, "rb")}
        except IOError as ex:
            logging.error("Problem opening audio file {}".format(opts.audio))
            raise

        if opts.text:
            try:
                files['text_file'] = open(opts.text, "rb")
            except IOError as ex:
                logging.error("Problem opening text file {}".format(opts.text))
                raise

        data = {"model": opts.lang}
        if "=" in data['model']:
            (data['model'], data['version']) = data['model'].split('=', 1)

        if opts.notification:
            data['notification'] = opts.notification
            if opts.notification == 'callback':
                data['callback'] = opts.callback_url
        if opts.notification_email:
            data['notification_email_address'] = opts.notification_email

        request = requests.post(url, data=data, files=files, params=params)
        if request.status_code == 200:
            json_out = json.loads(request.text)
            return json_out['id']
        else:
            err_msg = "Attempt to POST job failed with code {}\n".format(request.status_code)
            if request.status_code == 400:
                err_msg += ("Common causes of this error are:\n"
                            "Malformed arguments\n"
                            "Missing data file\n"
                            "Absent / unsupported language selection.")
            elif request.status_code == 401:
                err_msg += ("Common causes of this error are:\n"
                            "Invalid user id or authentication token.")
            elif request.status_code == 403:
                err_msg += ("Common causes of this error are:\n"
                            "Insufficient credit\n"
                            "User id not in our database\n"
                            "Incorrect authentication token.")
            elif request.status_code == 429:
                err_msg += ("Common causes of this error are:\n"
                            "You are submitting too many POSTs in a short period of time.")
            elif request.status_code == 503:
                err_msg += ("Common causes of this error are:\n"
                            "The system is temporarily unavailable or overloaded.\n"
                            "Your POST will typically succeed if you try again soon.")
            err_msg += ("\nIf you are still unsure why your POST failed please contact speechmatics:"
                        "support@speechmatics.com")
            raise SpeechmaticsError(err_msg)

    def job_details(self, job_id):
        """
        Checks on the status of the given job.

        If successfuly returns a dictionary of job details.
        """
        params = {'auth_token': self.api_token}
        url = "".join([self.base_url, '/user/', self.api_user_id, '/jobs/', str(job_id), '/'])
        request = requests.get(url, params=params)
        if request.status_code == 200:
            return json.loads(request.text)['job']
        else:
            err_msg = ("Attempt to GET job details failed with code {}\n"
                       "If you are still unsure why your POST failed please contact speechmatics:"
                       "support@speechmatics.com").format(request.status_code)
            raise SpeechmaticsError(err_msg)

    def get_output(self, job_id, frmat, job_type):
        """
        Downloads transcript for given transcription job.

        If successful returns the output.
        """
        params = {'auth_token': self.api_token}
        if frmat and job_type == 'transcript':
            params['format'] = 'txt'
        if frmat and job_type == 'alignment':
            params['tags'] = 'one_per_line'
        url = "".join([self.base_url, '/user/', self.api_user_id, '/jobs/', str(job_id), '/', job_type])
        request = requests.get(url, params=params)
        if request.status_code == 200:
            request.encoding = 'utf-8'
            return request.text
        else:
            err_msg = ("Attempt to GET job details failed with code {}\n"
                       "If you are still unsure why your POST failed please contact speechmatics:"
                       "support@speechmatics.com").format(request.status_code)
            raise SpeechmaticsError(err_msg)


def parse_args():
    """
    Parse command line arguments
    """

    # Parse the arguments
    parser = ArgumentParser(
        description='Processes a job through the Speechmatics API',
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-a', '--audio', type=str, required=True,
                        help="Audio file to be processed")
    parser.add_argument('-t', '--text', type=str, required=False,
                        help="Text file to be processed (only required for alignment jobs)", default=None)
    parser.add_argument('-o', '--output', type=str, required=False,
                        help="Output filename (will print to terminal if not specified)", default=None)
    parser.add_argument('-i', '--id', type=str, required=True,
                        help="Your Speechmatics user_id")
    parser.add_argument('-k', '--token', type=str, required=True,
                        help="Your Speechmatics API Authentication Token")
    parser.add_argument('-l', '--lang', type=str, required=True,
                        help="Code of language to use (e.g., en-US)")
    parser.add_argument('-f', '--format', action='store_true', required=False,
                        help="Return results in alternate format.\n"
                             "Default for transcription is json, alternate is text.\n"
                             "Default for alignment is one timing per word, alternate is one per line")
    parser.add_argument('-n', '--notification', type=str, choices=['email', 'none', 'callback'], required=False,
                        help="Type of notification to use (default is 'email').\n", default=None)
    parser.add_argument('-e', '--notification-email', type=str, required=False,
                        help="Alternative email address to send notification to upon job completion.\n", default=None)
    parser.add_argument('-u', '--callback-url', type=str, required=False,
                        help="Callback URL to use.", default=None)
    parsed = parser.parse_args()

    if parsed.notification_email is not None and parsed.notification in ['none', 'callback']:
        parser.error("You specified an alternative email address but selected '{}' notification.".format(parsed.notification))
    if parsed.notification == 'callback' and parsed.callback_url is None:
        parser.error("You selected notification type of callback but did not provide a callback URL.")

    return parsed


def main():
    """
    Example way to use the Speechmatics Client to process a job
    """
    logging.basicConfig(level=logging.INFO)

    opts = parse_args()

    client = SpeechmaticsClient(opts.id, opts.token)

    job_id = client.job_post(opts)
    logging.info("Your job has started with ID {}".format(job_id))

    details = client.job_details(job_id)

    while details[u'job_status'] not in ['done', 'expired', 'unsupported_file_format', 'could_not_align']:
        logging.info("Waiting for job to be processed.  Will check again in {} seconds".format(details['check_wait']))
        wait_s = details['check_wait']
        time.sleep(wait_s)
        details = client.job_details(job_id)

    if details['job_status'] == 'unsupported_file_format':
        raise SpeechmaticsError("File was in an unsupported file format and could not be transcribed. "
                                "You have been reimbursed all credits for this job.")

    if details['job_status'] == 'could_not_align':
        raise SpeechmaticsError("Could not align text and audio file. "
                                "You have been reimbursed all credits for this job.")

    logging.info("Processing complete, getting output")

    if details['job_type'] == 'transcription':
        job_type = 'transcript'
    elif details['job_type'] == 'alignment':
        job_type = 'alignment'
    output = client.get_output(job_id, opts.format, job_type)

    if opts.output:
        with codecs.open(opts.output, 'wt', 'utf-8') as ouf:
            if job_type == 'transcript' and opts.format:
                ouf.write(json.dumps(output, indent=4))
            else:
                ouf.write(output)
        logging.info("Your job output has been written to file {}".format(opts.output))
    else:
        logging.info("Your job output:")
        if job_type == 'transcript' and opts.format:
            print(json.dumps(output, indent=4))
        else:
            print(output.encode('utf-8'))


if __name__ == '__main__':
    main()
