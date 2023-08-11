import concurrent.futures
import requests
import util
import argparse
import eclypse
import backup

# If True, do not display SSL certificate verification warnings
SUPPRESS_SSL_WARNING = False


def create_backup(site, api_version):
    """Create a backup"""
    # Split input values
    hostname, username, password = site.values()

    # Create a session to make multiple requests
    with requests.session() as session:
        # ECLYPSE local API requires HTTP basic authentiation
        session.auth = (username,password)
        # Disable SSL certificate verification when using default self-signed certificate
        session.verify = False


        try:
            # If not specified, try to determine which API is supported
            if not api_version:
                api_version = eclypse.api_version(session, hostname) 

            # Call consolidated function
            results = backup.create(session, hostname)
            return {'host': hostname, 'scheduled': results.ok}
        
        # Allow the run to continue when a single ECLYPSE returns an error
        except requests.exceptions.ConnectTimeout:
            print(f'host: {hostname}, status: Device did not respond')
        except Exception as e:
            print(f'host: {hostname}, status: {str(e)}')


def main():
    parser = argparse.ArgumentParser(add_help=True, description="Create an Eclypse backup")
    parser.add_argument('host_file', default='./host_file', help='List of ECLYPSE controllers')
    parser.add_argument('-v', '--apiversion', choices=[1,2], required=False, type=int)

    args = parser.parse_args()

    # Disable warning for self-signed certificate
    if SUPPRESS_SSL_WARNING:
        requests.packages.urllib3.disable_warnings()

    # Script requires a list of ECLYPSE in a csv file
    # The csv file should contain information for 1 ECLYPSE per line
    # Required format is:
    # hostname,username,password
    host_list = util.read_host_list(args.host_file)

    # Concurrent futures manages the query of multiple ECLYPSE at the same time
    # max_workers determines the number of workers 
    # increase max_workers to decrease runtime
    # decrease max_workers to reduce CPU and bandwidth consumption
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        jobs = [executor.submit(create_backup, site, args.apiversion) for site in host_list]

        # Record result as each worker completes an upgrade job
        for job in concurrent.futures.as_completed(jobs):
            # Output result to screen and add to report
            if job.result() is not None:
                print(job.result())


if __name__ == "__main__":
    main()