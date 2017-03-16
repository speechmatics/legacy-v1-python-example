#!/usr/bin/python
"""
Example script for integrating with the Speechmatics API
"""

import codecs
import json
import sys
import time
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import requests


class SpeechmaticsClient(object):
    """
    A simple client to interact with the Speechmatics REST API
    Documentation at https://app.speechmatics.com/api-details
    """

    def __init__(self, api_user_id, api_token, base_url='https://api.speechmatics.com/v1.0'):
        self.api_user_id = api_user_id
        self.api_token = api_token
        self.base_url = base_url

    def job_post(self, audio_file, lang, text_file=None):
        """
        Upload a new audio file to speechmatics for transcription
        If text file is specified upload that as well for an alignment job
        If upload suceeds then this method will return the id of the new job

        If succesful returns an integer representing the job id
        If unsuccessful will print an error to terminal and exit(1)
        """

        url = "".join([self.base_url, '/user/', self.api_user_id, '/jobs/'])
        params = {'auth_token': self.api_token}
        try:
            files = {'data_file': open(audio_file, "rb")}
        except IOError as ex:
            print "Problem opening audio file {}".format(audio_file)
            print ex
            sys.exit(1)

        if text_file:
            try:
                files['text_file'] = open(text_file, "rb")
            except IOError as ex:
                print "Problem opening text file {}".format(text_file)
                print ex
                sys.exit(1)

        data = {"model": lang}

        try:
            request = requests.post(url, data=data, files=files, params=params)
            if request.status_code == 200:
                json_out = json.loads(request.text)
                return json_out['id']
            else:
                print "Attempt to POST job failed with code {}".format(request.status_code)
                if request.status_code == 400:
                    print ("Common causes of this error are:\n"
                           "Malformed arguments\n"
                           "Missing data file\n"
                           "Absent / unsupported language selection.")
                elif request.status_code == 401:
                    print ("Common causes of this error are:\n"
                           "Invalid user id or authentication token.")
                elif request.status_code == 403:
                    print ("Common causes of this error are:\n"
                           "Insufficient credit\n"
                           "User id not in our database\n"
                           "Incorrect authentication token.")
                elif request.status_code == 429:
                    print ("Common causes of this error are:\n"
                           "You are submitting too many POSTs in a short period of time.")
                elif request.status_code == 503:
                    print ("Common causes of this error are:\n"
                           "The system is temporarily unavailable or overloaded.\n"
                           "Your POST will typically succeed if you try again soon.")
                print ("If you are still unsure why your POST failed please contact speechmatics:"
                       "support@speechmatics.com")
                sys.exit(1)

        except requests.exceptions.RequestException as exc:
            print exc
            sys.exit(1)

    def job_details(self, job_id):
        """
        Checks on the status of the given job.

        If successfuly returns a dictionary of job details.
        If unsuccessful exit(1)
        """
        params = {'auth_token': self.api_token}
        url = "".join([self.base_url, '/user/', self.api_user_id, '/jobs/', str(job_id), '/'])
        try:
            request = requests.get(url, params=params)
            if request.status_code == 200:
                return json.loads(request.text)['job']
            else:
                print "Attempt to GET job details failed with code {}".format(request.status_code)
                print ("If you are still unsure why your POST failed please contact speechmatics:"
                       "support@speechmatics.com")
                sys.exit(1)

        except requests.exceptions.RequestException as exc:
            print exc
            sys.exit(1)

    def get_output(self, job_id, frmat, job_type):
        """
        Downloads transcript for given transcription job.

        If successful returns the output.
        If unsuccessful does exit(1)
        """
        params = {'auth_token': self.api_token}
        if frmat and job_type == 'transcription':
            params['format'] = 'txt'
        if frmat and job_type == 'alignment':
            params['tags'] = 'one_per_line'
        url = "".join([self.base_url, '/user/', self.api_user_id, '/jobs/', str(job_id), '/', job_type])
        try:
            request = requests.get(url, params=params)
            if request.status_code == 200:
                return request.text
            else:
                print "Attempt to GET job details failed with code {}".format(request.status_code)
                print ("If you are still unsure why your POST failed please contact speechmatics:"
                       "support@speechmatics.com")
                sys.exit(1)

        except requests.exceptions.RequestException as exc:
            print exc
            sys.exit(1)


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
    return parser.parse_args()


def main():
    """
    Example way to use the Speechmatics Client to process a job
    """
    opts = parse_args()

    client = SpeechmaticsClient(opts.id, opts.token)

    job_id = client.job_post(opts.audio, opts.lang, opts.text)
    print "Your job has started with ID {}".format(job_id)

    details = client.job_details(job_id)

    while details[u'job_status'] not in ['done', 'expired', 'unsupported_file_format', 'could_not_align']:
        print "Waiting for job to be processed.  Will check again in {} seconds".format(details['check_wait'])
        wait_s = details['check_wait']
        time.sleep(wait_s)
        details = client.job_details(job_id)

    if details['job_status'] == 'unsupported_file_format':
        print "File was in an unsupported file format and could not be transcribed."
        print "You have been reimbursed all credits for this job."
        sys.exit(1)

    if details['job_status'] == 'could_not_align':
        print "Could not align text and audio file."
        print "You have been reimbursed all credits for this job."
        sys.exit(1)

    print "Processing complete, getting output"

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
        print "Your job output has been written to file {}".format(opts.output)
    else:
        print "Your job output:"
        if job_type == 'transcript' and opts.format:
            print json.dumps(output, indent=4)
        else:
            print output


if __name__ == '__main__':
    main()
