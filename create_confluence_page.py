#!/usr/bin/env python3
"""
Confluence SOP Page Creator Script

This script creates professional SOP (Standard Operating Procedure) pages in Confluence
using a comprehensive template with proper formatting, structure, and design.

Requirements:
    pip install requests

Usage:
    python create_confluence_page.py

Configuration:
    Set environment variables or modify the config section:
    - CONFLUENCE_URL: Your Confluence instance URL
    - CONFLUENCE_EMAIL: Your Atlassian account email
    - CONFLUENCE_API_TOKEN: Your API token (create at https://id.atlassian.com/manage-profile/security/api-tokens)
"""

import os
import sys
import json
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime


class ConfluenceClient:
    """Client for interacting with Confluence REST API"""

    def __init__(self, base_url: str, email: str, api_token: str):
        """
        Initialize the Confluence client

        Args:
            base_url: Base URL of your Confluence instance (e.g., https://yourcompany.atlassian.net)
            email: Your Atlassian account email
            api_token: Your API token
        """
        self.base_url = base_url.rstrip('/')
        self.auth = (email, api_token)
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Get page information by ID

        Args:
            page_id: The Confluence page ID

        Returns:
            Page data or None if not found
        """
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}"
        params = {'expand': 'body.storage,version,space'}

        response = requests.get(url, auth=self.auth, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"Page {page_id} not found")
            return None
        else:
            print(f"Error getting page: {response.status_code}")
            print(response.text)
            return None

    def create_page(
        self,
        space_key: str,
        title: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new Confluence page

        Args:
            space_key: The space key (e.g., 'MDS')
            title: Page title
            content: Page content in Confluence storage format (HTML-like)
            parent_id: Optional parent page ID

        Returns:
            Created page data or None on failure
        """
        url = f"{self.base_url}/wiki/rest/api/content"

        payload = {
            'type': 'page',
            'title': title,
            'space': {'key': space_key},
            'body': {
                'storage': {
                    'value': content,
                    'representation': 'storage'
                }
            }
        }

        if parent_id:
            payload['ancestors'] = [{'id': parent_id}]

        response = requests.post(
            url,
            auth=self.auth,
            headers=self.headers,
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            page = response.json()
            print(f"✓ Page created successfully!")
            print(f"  Title: {page['title']}")
            print(f"  ID: {page['id']}")
            print(f"  URL: {self.base_url}/wiki{page['_links']['webui']}")
            return page
        else:
            print(f"✗ Error creating page: {response.status_code}")
            print(response.text)
            return None

    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        version: int
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing Confluence page

        Args:
            page_id: The page ID to update
            title: New page title
            content: New page content in Confluence storage format
            version: Current version number (will increment by 1)

        Returns:
            Updated page data or None on failure
        """
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}"

        payload = {
            'id': page_id,
            'type': 'page',
            'title': title,
            'body': {
                'storage': {
                    'value': content,
                    'representation': 'storage'
                }
            },
            'version': {
                'number': version + 1
            }
        }

        response = requests.put(
            url,
            auth=self.auth,
            headers=self.headers,
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            page = response.json()
            print(f"✓ Page updated successfully!")
            print(f"  Title: {page['title']}")
            print(f"  ID: {page['id']}")
            print(f"  Version: {page['version']['number']}")
            print(f"  URL: {self.base_url}/wiki{page['_links']['webui']}")
            return page
        else:
            print(f"✗ Error updating page: {response.status_code}")
            print(response.text)
            return None

    def publish_draft(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Publish a draft page

        Args:
            page_id: The draft page ID

        Returns:
            Published page data or None on failure
        """
        # Get the current draft
        page = self.get_page(page_id)
        if not page:
            return None

        # Update the page to publish it (drafts are published by updating them)
        return self.update_page(
            page_id=page_id,
            title=page['title'],
            content=page['body']['storage']['value'],
            version=page['version']['number']
        )


class SOPTemplate:
    """SOP Template Generator for Confluence"""

    @staticmethod
    def create_sop_content(sop_data: Dict[str, Any]) -> str:
        """
        Generate a professionally formatted SOP page in Confluence storage format

        Args:
            sop_data: Dictionary containing SOP information

        Returns:
            HTML content in Confluence storage format
        """
        # Extract data with defaults
        title = sop_data.get('title', 'Standard Operating Procedure')
        doc_id = sop_data.get('doc_id', 'SOP-001')
        version = sop_data.get('version', '1.0')
        effective_date = sop_data.get('effective_date', datetime.now().strftime('%Y-%m-%d'))
        review_date = sop_data.get('review_date', '')
        owner = sop_data.get('owner', '')
        department = sop_data.get('department', '')

        purpose = sop_data.get('purpose', '')
        scope = sop_data.get('scope', '')
        responsibilities = sop_data.get('responsibilities', [])
        definitions = sop_data.get('definitions', [])
        procedures = sop_data.get('procedures', [])
        references = sop_data.get('references', [])
        attachments = sop_data.get('attachments', [])
        revision_history = sop_data.get('revision_history', [])

        # Build the HTML content
        html = f"""
<ac:structured-macro ac:name="info" ac:schema-version="1">
  <ac:rich-text-body>
    <p><strong>Document Control Information</strong></p>
    <table>
      <tbody>
        <tr>
          <td><strong>Document ID:</strong></td>
          <td>{doc_id}</td>
          <td><strong>Version:</strong></td>
          <td>{version}</td>
        </tr>
        <tr>
          <td><strong>Effective Date:</strong></td>
          <td>{effective_date}</td>
          <td><strong>Review Date:</strong></td>
          <td>{review_date}</td>
        </tr>
        <tr>
          <td><strong>Owner:</strong></td>
          <td>{owner}</td>
          <td><strong>Department:</strong></td>
          <td>{department}</td>
        </tr>
      </tbody>
    </table>
  </ac:rich-text-body>
</ac:structured-macro>

<p></p>

<ac:structured-macro ac:name="toc" ac:schema-version="1">
  <ac:parameter ac:name="maxLevel">3</ac:parameter>
  <ac:parameter ac:name="minLevel">1</ac:parameter>
  <ac:parameter ac:name="exclude"></ac:parameter>
  <ac:parameter ac:name="type">list</ac:parameter>
  <ac:parameter ac:name="outline">clear</ac:parameter>
  <ac:parameter ac:name="style">disc</ac:parameter>
</ac:structured-macro>

<p></p>
<hr />

<h2>1. Purpose</h2>
<p>{purpose or 'Define the purpose and objective of this procedure.'}</p>

<h2>2. Scope</h2>
<p>{scope or 'Describe the scope and applicability of this procedure.'}</p>

<h2>3. Definitions and Acronyms</h2>
"""

        if definitions:
            html += "<table><tbody>\n"
            html += "<tr><th>Term</th><th>Definition</th></tr>\n"
            for definition in definitions:
                term = definition.get('term', '')
                meaning = definition.get('definition', '')
                html += f"<tr><td><strong>{term}</strong></td><td>{meaning}</td></tr>\n"
            html += "</tbody></table>\n"
        else:
            html += "<p>No definitions or acronyms specified.</p>\n"

        html += """
<h2>4. Roles and Responsibilities</h2>
"""

        if responsibilities:
            html += "<table><tbody>\n"
            html += "<tr><th>Role</th><th>Responsibilities</th></tr>\n"
            for responsibility in responsibilities:
                role = responsibility.get('role', '')
                duties = responsibility.get('duties', '')
                html += f"<tr><td><strong>{role}</strong></td><td>{duties}</td></tr>\n"
            html += "</tbody></table>\n"
        else:
            html += "<p>Define roles and responsibilities for this procedure.</p>\n"

        html += """
<h2>5. Procedure</h2>
"""

        if procedures:
            for i, procedure in enumerate(procedures, 1):
                step_title = procedure.get('title', f'Step {i}')
                html += f"<h3>5.{i} {step_title}</h3>\n"

                description = procedure.get('description', '')
                if description:
                    html += f"<p>{description}</p>\n"

                substeps = procedure.get('substeps', [])
                if substeps:
                    html += "<ol>\n"
                    for substep in substeps:
                        html += f"<li>{substep}</li>\n"
                    html += "</ol>\n"

                # Add notes/warnings if present
                notes = procedure.get('notes', '')
                if notes:
                    html += f"""
<ac:structured-macro ac:name="note" ac:schema-version="1">
  <ac:rich-text-body>
    <p>{notes}</p>
  </ac:rich-text-body>
</ac:structured-macro>
"""

                warnings = procedure.get('warnings', '')
                if warnings:
                    html += f"""
<ac:structured-macro ac:name="warning" ac:schema-version="1">
  <ac:rich-text-body>
    <p>{warnings}</p>
  </ac:rich-text-body>
</ac:structured-macro>
"""
        else:
            html += "<p>Document the step-by-step procedure here.</p>\n"

        html += """
<h2>6. Related Documents and References</h2>
"""

        if references:
            html += "<ul>\n"
            for reference in references:
                html += f"<li>{reference}</li>\n"
            html += "</ul>\n"
        else:
            html += "<p>No related documents or references.</p>\n"

        html += """
<h2>7. Attachments</h2>
"""

        if attachments:
            html += "<ul>\n"
            for attachment in attachments:
                html += f"<li>{attachment}</li>\n"
            html += "</ul>\n"
        else:
            html += "<p>No attachments.</p>\n"

        html += """
<hr />

<h2>Revision History</h2>
"""

        if revision_history:
            html += "<table><tbody>\n"
            html += "<tr><th>Version</th><th>Date</th><th>Author</th><th>Description of Changes</th></tr>\n"
            for revision in revision_history:
                ver = revision.get('version', '')
                date = revision.get('date', '')
                author = revision.get('author', '')
                changes = revision.get('changes', '')
                html += f"<tr><td>{ver}</td><td>{date}</td><td>{author}</td><td>{changes}</td></tr>\n"
            html += "</tbody></table>\n"
        else:
            html += """
<table><tbody>
<tr><th>Version</th><th>Date</th><th>Author</th><th>Description of Changes</th></tr>
<tr><td>1.0</td><td>""" + effective_date + """</td><td>""" + owner + """</td><td>Initial version</td></tr>
</tbody></table>
"""

        html += """
<p></p>

<ac:structured-macro ac:name="info" ac:schema-version="1">
  <ac:rich-text-body>
    <p><strong>Document Approval</strong></p>
    <p>This document has been reviewed and approved by the appropriate stakeholders.</p>
  </ac:rich-text-body>
</ac:structured-macro>
"""

        return html


def load_config() -> Dict[str, str]:
    """Load configuration from environment variables or prompt user"""
    # Try to load from .env file if it exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print("Loading configuration from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

    config = {}

    # Confluence URL
    config['url'] = os.getenv('CONFLUENCE_URL', 'https://grantthorntonsupport.atlassian.net')

    # Email
    config['email'] = os.getenv('CONFLUENCE_EMAIL', '')
    if not config['email']:
        config['email'] = input('Enter your Atlassian email: ').strip()

    # API Token
    config['api_token'] = os.getenv('CONFLUENCE_API_TOKEN', '')
    if not config['api_token']:
        print('\nTo create an API token:')
        print('1. Visit: https://id.atlassian.com/manage-profile/security/api-tokens')
        print('2. Click "Create API token"')
        print('3. Copy the token and paste it below\n')
        config['api_token'] = input('Enter your API token: ').strip()

    return config


def get_user_input(prompt: str, default: str = '') -> str:
    """Get user input with optional default value"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()


def get_multiline_input(prompt: str) -> str:
    """Get multiline input from user"""
    print(f"\n{prompt}")
    print("(Enter text, then press Ctrl+D on Unix or Ctrl+Z on Windows when done)")
    print("-" * 60)

    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass

    return '\n'.join(lines).strip()


def collect_sop_data_interactive() -> Dict[str, Any]:
    """Interactively collect SOP data from user"""
    print("\n" + "=" * 60)
    print("SOP INFORMATION COLLECTION")
    print("=" * 60)

    sop_data = {}

    # Basic information
    print("\n--- Basic Information ---")
    sop_data['title'] = get_user_input("SOP Title", "Standard Operating Procedure")
    sop_data['doc_id'] = get_user_input("Document ID", "SOP-001")
    sop_data['version'] = get_user_input("Version", "1.0")
    sop_data['effective_date'] = get_user_input("Effective Date (YYYY-MM-DD)",
                                                  datetime.now().strftime('%Y-%m-%d'))
    sop_data['review_date'] = get_user_input("Next Review Date (YYYY-MM-DD)", "")
    sop_data['owner'] = get_user_input("Document Owner")
    sop_data['department'] = get_user_input("Department")

    # Purpose and Scope
    print("\n--- Purpose and Scope ---")
    sop_data['purpose'] = get_multiline_input("Enter the PURPOSE of this SOP:")
    sop_data['scope'] = get_multiline_input("Enter the SCOPE of this SOP:")

    # Definitions
    print("\n--- Definitions and Acronyms ---")
    definitions = []
    while True:
        add_def = input("\nAdd a definition/acronym? (y/n): ").strip().lower()
        if add_def != 'y':
            break
        term = get_user_input("Term/Acronym")
        definition = get_user_input("Definition")
        definitions.append({'term': term, 'definition': definition})
    sop_data['definitions'] = definitions

    # Responsibilities
    print("\n--- Roles and Responsibilities ---")
    responsibilities = []
    while True:
        add_resp = input("\nAdd a role? (y/n): ").strip().lower()
        if add_resp != 'y':
            break
        role = get_user_input("Role Title")
        duties = get_multiline_input(f"Enter responsibilities for {role}:")
        responsibilities.append({'role': role, 'duties': duties})
    sop_data['responsibilities'] = responsibilities

    # Procedures
    print("\n--- Procedure Steps ---")
    procedures = []
    step_num = 1
    while True:
        add_proc = input(f"\nAdd procedure step {step_num}? (y/n): ").strip().lower()
        if add_proc != 'y':
            break

        step = {}
        step['title'] = get_user_input(f"Step {step_num} Title")
        step['description'] = get_multiline_input(f"Enter description for step {step_num}:")

        # Substeps
        substeps = []
        while True:
            add_substep = input(f"Add a substep to step {step_num}? (y/n): ").strip().lower()
            if add_substep != 'y':
                break
            substep = get_user_input("Substep")
            substeps.append(substep)
        step['substeps'] = substeps

        # Notes and warnings
        add_note = input("Add a note for this step? (y/n): ").strip().lower()
        if add_note == 'y':
            step['notes'] = get_multiline_input("Enter note:")

        add_warning = input("Add a warning for this step? (y/n): ").strip().lower()
        if add_warning == 'y':
            step['warnings'] = get_multiline_input("Enter warning:")

        procedures.append(step)
        step_num += 1

    sop_data['procedures'] = procedures

    # References
    print("\n--- References ---")
    references = []
    while True:
        add_ref = input("\nAdd a reference/related document? (y/n): ").strip().lower()
        if add_ref != 'y':
            break
        reference = get_user_input("Reference")
        references.append(reference)
    sop_data['references'] = references

    # Revision History
    print("\n--- Revision History ---")
    revision_history = []
    add_history = input("\nAdd revision history entries? (y/n): ").strip().lower()
    if add_history == 'y':
        while True:
            add_rev = input("\nAdd a revision? (y/n): ").strip().lower()
            if add_rev != 'y':
                break
            revision = {
                'version': get_user_input("Version"),
                'date': get_user_input("Date (YYYY-MM-DD)"),
                'author': get_user_input("Author"),
                'changes': get_user_input("Description of Changes")
            }
            revision_history.append(revision)
    sop_data['revision_history'] = revision_history

    return sop_data


def main():
    """Main function"""
    print("=" * 60)
    print("Confluence SOP Page Creator")
    print("=" * 60)
    print()

    # Load configuration
    config = load_config()

    # Create client
    client = ConfluenceClient(
        base_url=config['url'],
        email=config['email'],
        api_token=config['api_token']
    )

    # Menu
    print("\nWhat would you like to do?")
    print("1. Create a new SOP page (Interactive)")
    print("2. Create SOP from JSON file")
    print("3. Publish an existing draft")
    print("4. Create a new page (Custom content)")
    print("5. Update an existing page")
    print("6. Get page information")

    choice = input("\nEnter your choice (1-6): ").strip()

    if choice == '1':
        # Create new SOP interactively
        print("\n" + "=" * 60)
        print("INTERACTIVE SOP CREATION")
        print("=" * 60)

        # Collect SOP data
        sop_data = collect_sop_data_interactive()

        # Generate content
        print("\n\nGenerating SOP content...")
        content = SOPTemplate.create_sop_content(sop_data)

        # Get Confluence details
        space_key = get_user_input("\nEnter Confluence space key", "MDS")
        parent_id = get_user_input("Enter parent page ID (optional)", "")

        # Confirm creation
        print("\n" + "=" * 60)
        print("READY TO CREATE SOP PAGE")
        print("=" * 60)
        print(f"Title: {sop_data['title']}")
        print(f"Space: {space_key}")
        print(f"Parent: {parent_id if parent_id else 'None (top level)'}")

        confirm = input("\nCreate this SOP page? (y/n): ").strip().lower()
        if confirm == 'y':
            client.create_page(
                space_key=space_key,
                title=sop_data['title'],
                content=content,
                parent_id=parent_id if parent_id else None
            )
        else:
            print("SOP creation cancelled.")

            # Offer to save to file
            save = input("Save SOP data to JSON file? (y/n): ").strip().lower()
            if save == 'y':
                filename = get_user_input("Filename", "sop_data.json")
                with open(filename, 'w') as f:
                    json.dump(sop_data, f, indent=2)
                print(f"SOP data saved to {filename}")

    elif choice == '2':
        # Create SOP from JSON file
        filename = get_user_input("\nEnter JSON filename")

        if not os.path.exists(filename):
            print(f"Error: File {filename} not found")
            return

        with open(filename, 'r') as f:
            sop_data = json.load(f)

        # Generate content
        print("Generating SOP content from JSON...")
        content = SOPTemplate.create_sop_content(sop_data)

        # Get Confluence details
        space_key = get_user_input("Enter Confluence space key", "MDS")
        parent_id = get_user_input("Enter parent page ID (optional)", "")

        # Create page
        title = sop_data.get('title', 'Standard Operating Procedure')
        print(f"\nCreating SOP page '{title}'...")
        client.create_page(
            space_key=space_key,
            title=title,
            content=content,
            parent_id=parent_id if parent_id else None
        )

    elif choice == '3':
        # Publish draft
        page_id = input("\nEnter the draft page ID (from URL): ").strip()
        # Default to the page ID from your URL
        if not page_id:
            page_id = '671023108'

        print(f"\nPublishing draft {page_id}...")
        client.publish_draft(page_id)

    elif choice == '4':
        # Create new page
        space_key = input("\nEnter space key (e.g., MDS): ").strip() or 'MDS'
        title = input("Enter page title: ").strip()

        print("\nEnter page content (Confluence storage format).")
        print("You can paste HTML or use simple HTML tags.")
        print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done:")

        content_lines = []
        try:
            while True:
                line = input()
                content_lines.append(line)
        except EOFError:
            pass

        content = '\n'.join(content_lines)

        # If content is empty, use a default
        if not content.strip():
            content = '<p>This is a new page.</p>'

        parent_id = input("\nEnter parent page ID (optional, press Enter to skip): ").strip()

        print(f"\nCreating page '{title}' in space '{space_key}'...")
        client.create_page(
            space_key=space_key,
            title=title,
            content=content,
            parent_id=parent_id if parent_id else None
        )

    elif choice == '5':
        # Update existing page
        page_id = input("\nEnter page ID: ").strip()

        # Get current page
        page = client.get_page(page_id)
        if not page:
            return

        print(f"\nCurrent title: {page['title']}")
        title = input("Enter new title (or press Enter to keep current): ").strip()
        if not title:
            title = page['title']

        print("\nEnter new content (or press Enter to keep current):")
        print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done:")

        content_lines = []
        try:
            while True:
                line = input()
                content_lines.append(line)
        except EOFError:
            pass

        content = '\n'.join(content_lines)
        if not content.strip():
            content = page['body']['storage']['value']

        print(f"\nUpdating page {page_id}...")
        client.update_page(
            page_id=page_id,
            title=title,
            content=content,
            version=page['version']['number']
        )

    elif choice == '6':
        # Get page info
        page_id = input("\nEnter page ID: ").strip()
        page = client.get_page(page_id)

        if page:
            print("\n" + "=" * 60)
            print("Page Information")
            print("=" * 60)
            print(f"Title: {page['title']}")
            print(f"ID: {page['id']}")
            print(f"Type: {page['type']}")
            print(f"Space: {page['space']['key']}")
            print(f"Version: {page['version']['number']}")
            print(f"URL: {config['url']}/wiki{page['_links']['webui']}")
            print("\nContent preview:")
            print("-" * 60)
            print(page['body']['storage']['value'][:500])
            if len(page['body']['storage']['value']) > 500:
                print("... (truncated)")

    else:
        print("Invalid choice")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
