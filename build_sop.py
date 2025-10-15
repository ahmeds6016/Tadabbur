#!/usr/bin/env python3
"""
Simple script to build an SOP page in Confluence from your draft.
Just run it and enter your credentials and the SOP content.
"""

import os
import sys
import requests
import json
from datetime import datetime


def create_sop_page(base_url, email, api_token, space_key, title, sop_content):
    """Create an SOP page in Confluence"""

    url = f"{base_url}/wiki/rest/api/content"
    auth = (email, api_token)
    headers = {'Content-Type': 'application/json'}

    # Generate the SOP HTML content
    html = f"""
<ac:structured-macro ac:name="info" ac:schema-version="1">
  <ac:rich-text-body>
    <p><strong>Document Control Information</strong></p>
    <table>
      <tbody>
        <tr>
          <td><strong>Document ID:</strong></td>
          <td>{sop_content.get('doc_id', 'SOP-001')}</td>
          <td><strong>Version:</strong></td>
          <td>{sop_content.get('version', '1.0')}</td>
        </tr>
        <tr>
          <td><strong>Effective Date:</strong></td>
          <td>{sop_content.get('effective_date', datetime.now().strftime('%Y-%m-%d'))}</td>
          <td><strong>Owner:</strong></td>
          <td>{sop_content.get('owner', '')}</td>
        </tr>
      </tbody>
    </table>
  </ac:rich-text-body>
</ac:structured-macro>

<ac:structured-macro ac:name="toc" ac:schema-version="1">
  <ac:parameter ac:name="maxLevel">3</ac:parameter>
</ac:structured-macro>

<hr />

<h2>1. Purpose</h2>
<p>{sop_content.get('purpose', 'Define the purpose of this procedure.')}</p>

<h2>2. Scope</h2>
<p>{sop_content.get('scope', 'Define the scope of this procedure.')}</p>

<h2>3. Procedure</h2>
"""

    # Add procedure steps
    for i, step in enumerate(sop_content.get('steps', []), 1):
        html += f"<h3>{i}. {step['title']}</h3>\n"
        html += f"<p>{step['description']}</p>\n"

        if step.get('substeps'):
            html += "<ol>\n"
            for substep in step['substeps']:
                html += f"<li>{substep}</li>\n"
            html += "</ol>\n"

    html += """
<hr />
<h2>Revision History</h2>
<table>
  <tbody>
    <tr><th>Version</th><th>Date</th><th>Author</th><th>Changes</th></tr>
"""

    for rev in sop_content.get('revisions', []):
        html += f"<tr><td>{rev['version']}</td><td>{rev['date']}</td><td>{rev['author']}</td><td>{rev['changes']}</td></tr>\n"

    html += """
  </tbody>
</table>
"""

    # Create the page
    payload = {
        'type': 'page',
        'title': title,
        'space': {'key': space_key},
        'body': {
            'storage': {
                'value': html,
                'representation': 'storage'
            }
        }
    }

    response = requests.post(url, auth=auth, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        page = response.json()
        print(f"\n✓ SOP page created successfully!")
        print(f"  URL: {base_url}/wiki{page['_links']['webui']}")
        return page
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.text)
        return None


def main():
    print("=" * 60)
    print("Simple SOP Builder for Confluence")
    print("=" * 60)

    # Get credentials
    email = input("\nYour Atlassian email: ").strip()
    api_token = input("Your API token: ").strip()

    # Define your SOP content here
    sop_content = {
        'doc_id': 'SOP-001',
        'version': '1.0',
        'effective_date': '2025-10-14',
        'owner': 'Your Name',
        'purpose': 'This SOP describes the standard procedure for [your process].',
        'scope': 'This applies to [scope details].',
        'steps': [
            {
                'title': 'Step 1: Preparation',
                'description': 'Describe what to do in this step.',
                'substeps': [
                    'First substep',
                    'Second substep',
                    'Third substep'
                ]
            },
            {
                'title': 'Step 2: Execution',
                'description': 'Describe the main execution.',
                'substeps': [
                    'Action 1',
                    'Action 2',
                    'Action 3'
                ]
            },
            {
                'title': 'Step 3: Verification',
                'description': 'Verify the results.',
                'substeps': [
                    'Check 1',
                    'Check 2',
                    'Check 3'
                ]
            }
        ],
        'revisions': [
            {
                'version': '1.0',
                'date': '2025-10-14',
                'author': 'Your Name',
                'changes': 'Initial version'
            }
        ]
    }

    # Get Confluence details
    space_key = input("\nSpace key [MDS]: ").strip() or 'MDS'
    title = input("SOP Title: ").strip()

    # Create the page
    print("\nCreating SOP page...")
    create_sop_page(
        base_url='https://grantthorntonsupport.atlassian.net',
        email=email,
        api_token=api_token,
        space_key=space_key,
        title=title,
        sop_content=sop_content
    )


if __name__ == '__main__':
    main()
