import sys
import subprocess
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

BASE_URL = 'https://v5pah3m82k.ap-south-1.awsapprunner.com'

def run_test():
    print('Testing /notice/analyze...')
    payload_analyze = {
        'company_name_hint': 'FlightCo',
        'issue_summary': 'My flight was cancelled without refund.',
        'desired_resolution': 'Full refund please.',
        'company_objection': 'We do not owe you anything.'
    }
    r = requests.post(f'{BASE_URL}/notice/analyze', json=payload_analyze)
    print("Analyze status code:", r.status_code)
    try:
        if r.status_code == 200:
            print("Analyze First 2 questions:", r.json().get('questions', [])[:2])
    except Exception as e:
        print("Analyze failed to parse JSON:", e)
        print("Analyze Response body:", r.text)
    
    if r.status_code != 200:
        print("Analyze response:", r.text)
        return
    
    questions = r.json().get('questions', [])

    print('\nTesting /notice/typed...')
    payload_typed = {
        'company_name_hint': 'FlightCo',
        'issue_summary': 'My flight was cancelled without refund.',
        'desired_resolution': 'Full refund please.',
        'company_objection': 'We do not owe you anything.',
        'company_state': 'CA',
        'complainant_state': 'CA',
        'followup_answers': {q['id']: 'Test answer' for q in questions},
        'complainant': {
            'full_name': 'Amit Sharma',
            'email': 'john@example.com',
            'phone': '1234567890',
            'state': 'CA'
        }
    }
    
    r2 = requests.post(f'{BASE_URL}/notice/typed', json=payload_typed)
    print("Typed Notice status code:", r2.status_code)
    try:
        response_json = r2.json()
        print("Typed notice keys:", response_json.keys())
        job_id = response_json.get('job_id')
        poll_token = response_json.get('poll_token', '')
        if job_id:
            import time
            while True:
                r_job = requests.get(f'{BASE_URL}/notice/job/{job_id}', params={'poll_token': poll_token})
                job_data = r_job.json()
                print(f"Job status: {job_data.get('status')}")
                if job_data.get('status') in ['completed', 'failed']:
                    if job_data.get('status') == 'completed':
                        result = job_data.get('result', {})
                        print("Full Result:", result)
                    else:
                        print("Job Failed:", job_data.get('error'))
                    break
                time.sleep(2)
    except Exception as e:
        print("Typed Notice failed to parse JSON:", e)
        print("Typed Notice response:", r2.text)

if __name__ == '__main__':
    run_test()
