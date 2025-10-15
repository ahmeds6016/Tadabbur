#!/usr/bin/env python3
"""
Build Exabeam Incident Response Playbook SOP in Confluence
"""

import requests
import json
from datetime import datetime


def create_exabeam_sop(base_url, email, api_token, space_key, parent_id=None):
    """Create the Exabeam Incident Response SOP in Confluence"""

    url = f"{base_url}/wiki/rest/api/content"
    auth = (email, api_token)
    headers = {'Content-Type': 'application/json'}

    title = "Exabeam Incident Response Playbook (SOP) - Sequential Execution"

    # Build the HTML content
    html = """
<ac:structured-macro ac:name="info" ac:schema-version="1">
  <ac:rich-text-body>
    <p><strong>Document Control Information</strong></p>
    <table>
      <tbody>
        <tr>
          <td><strong>Document ID:</strong></td>
          <td>SOP-EXABEAM-IR-001</td>
          <td><strong>Version:</strong></td>
          <td>1.0</td>
        </tr>
        <tr>
          <td><strong>Effective Date:</strong></td>
          <td>""" + datetime.now().strftime('%Y-%m-%d') + """</td>
          <td><strong>Owner:</strong></td>
          <td>Security Operations Team</td>
        </tr>
      </tbody>
    </table>
  </ac:rich-text-body>
</ac:structured-macro>

<p></p>

<ac:structured-macro ac:name="toc" ac:schema-version="1">
  <ac:parameter ac:name="maxLevel">3</ac:parameter>
</ac:structured-macro>

<hr />

<h2>Phase 1: Triage &amp; Initial Assessment</h2>

<h3>1.1 Access &amp; Navigate to Incidents</h3>
<ol>
<li><strong>OPEN</strong> client UBA home page: <a href="https://client.aa.exabeam.com/uba/#home">https://client.aa.exabeam.com/uba/#home</a></li>
<li><strong>CLICK</strong> "Incidents" (left pane, third option)</li>
<li><strong>CLICK</strong> Queue Filter dropdown → <strong>SELECT</strong> "Analysts Queue"</li>
<li><strong>CLICK</strong> Status dropdown → <strong>CLICK</strong> Reset → <strong>SELECT</strong> "New"</li>
<li><strong>VERIFY</strong> you see only unassigned new incidents</li>
</ol>

<h3>1.2 Assign Incident &amp; Set Status</h3>
<ol>
<li><strong>CLICK</strong> the incident you intend to work on</li>
<li><strong>CLICK</strong> "Unassigned" link → <strong>SELECT</strong> your name from dropdown</li>
<li><strong>CLICK</strong> "New" status → <strong>CHANGE</strong> to "In Progress"</li>
<li><strong>VERIFY</strong> incident is now assigned to you and in progress</li>
</ol>

<h3>1.3 Review Incident Context</h3>
<ol>
<li><strong>LOCATE</strong> the Behavioral Analytics section in the incident view</li>
<li><strong>READ</strong> the incident description and triggering rules to get initial understanding of type of incident investigating</li>
<li><strong>IDENTIFY</strong> the following:
  <ul>
    <li>Rule Count</li>
    <li>Event Count</li>
    <li>Exabeam Risk Score</li>
    <li>Risk Reason list</li>
  </ul>
</li>
</ol>

<h3>1.4 Investigate Entity</h3>
<ol>
<li><strong>CLICK</strong> "Timeline Page" link for the entity</li>
<li><strong>COPY</strong> the timeline URL and paste into case notes for reference</li>
<li><strong>CLICK</strong> entity name/profile link to open entity information page</li>
<li><strong>REVIEW</strong> entity contextual information displayed</li>
</ol>

<h3>1.5 Collect General Entity Information</h3>

<p><strong>FOR USER ENTITIES: DOCUMENT the following information:</strong></p>
<ul>
<li>Full name (<strong>REQUIRED</strong>)</li>
<li>Job title (<strong>REQUIRED</strong>)</li>
<li>Location (<strong>REQUIRED IF PRESENT</strong>)</li>
<li>Labels (executive, privileged, etc.) (<strong>REQUIRED IF PRESENT</strong>)</li>
<li>First seen date (<strong>IF RELEVANT</strong>)</li>
<li>Last seen date (<strong>IF RELEVANT</strong>)</li>
<li>Department (<strong>REQUIRED IF PRESENT</strong>)</li>
<li>Manager name (<strong>IF RELEVANT</strong>)</li>
<li>Top peer group (<strong>IF RELEVANT</strong>)</li>
<li>Account status (active/disabled/locked) (<strong>IF RELEVANT</strong>)</li>
<li>Employee type (<strong>IF RELEVANT</strong>)</li>
<li>Last password reset date (<strong>IF RELEVANT</strong>)</li>
</ul>

<p><strong>FOR ASSET ENTITIES: DOCUMENT the following information:</strong></p>
<ul>
<li>Asset name (<strong>REQUIRED</strong>)</li>
<li>IP address (<strong>REQUIRED</strong>)</li>
<li>Asset labels (<strong>REQUIRED</strong>)</li>
<li>Network zone (<strong>IF RELEVANT</strong>)</li>
<li>Physical location (<strong>IF RELEVANT</strong>)</li>
<li>Top user (most frequent user) (<strong>IF RELEVANT</strong>)</li>
<li>First seen date (<strong>IF RELEVANT</strong>)</li>
<li>Last seen date (<strong>IF RELEVANT</strong>)</li>
</ul>

<hr />

<h2>Phase 2: Mandatory Case Note Creation &amp; First Exit Ramp</h2>

<p><strong>EXECUTE the following case note creation sequence EXACTLY in this order:</strong></p>

<h3>2.1 CREATE Entity Information Case Note</h3>
<ol>
<li><strong>CLICK</strong> "Add Note" or equivalent in case management</li>
<li><strong>TITLE:</strong> "Entity Information"</li>
<li><strong>COPY/PASTE</strong> the relevant entity information collected in 1.5</li>
<li><strong>ADD</strong> session timeline URL: "Timeline Link: [URL]"</li>
<li><strong>SAVE</strong> the case note</li>
</ol>

<h3>2.2 CREATE Risk Score Case Note</h3>
<ol>
<li><strong>CLICK</strong> "Add Note"</li>
<li><strong>TITLE:</strong> "Risk Score Analysis"</li>
<li><strong>COPY</strong> the entity's risk score from the incident</li>
<li><strong>PASTE</strong> into case notes with format:<br/>
<pre>Risk Score: [X]
Session Type: [User Session/Asset Session/Daily Feed/Lockout Sequence]
Incident Event URL: [Copy URL from browser]</pre>
</li>
<li><strong>SAVE</strong> the case note</li>
</ol>

<h3>2.3 CREATE Risk Reasons Case Note</h3>
<ol>
<li><strong>CLICK</strong> "Add Note"</li>
<li><strong>TITLE:</strong> "Risk Reasons"</li>
<li><strong>NAVIGATE</strong> to Risk Reasons section</li>
<li><strong>COPY</strong> rules that:
  <ul>
    <li>Added &gt;10 points, OR</li>
    <li>Added &lt;10 points but are relevant to the incident</li>
  </ul>
</li>
<li><strong>PASTE</strong> into case notes, then clean formatting:
  <ul>
    <li>Remove "+NUMBERS"</li>
    <li>Keep only rule name and count of occurrences (if provided)</li>
    <li>Space rules for readability</li>
  </ul>
</li>
<li><strong>EXAMPLE</strong> (Cleaned):<br/>
<pre>12× First login to an application for a user with no history
New user has uploaded 20MB
User with no web activity history accessing file sharing website</pre>
</li>
<li><strong>SAVE</strong> the case note</li>
</ol>

<h3>2.4 CREATE Main Risk Reason / Key Artifact Case Note</h3>
<ol>
<li><strong>CLICK</strong> "Add Note"</li>
<li><strong>TITLE:</strong> "Primary Risk Analysis"</li>
<li><strong>IDENTIFY</strong> the highest-scoring risk reason</li>
<li><strong>CLICK</strong> on that risk reason to expand details</li>
<li><strong>DOCUMENT</strong> for each relevant risk reason:
  <ul>
    <li>Rule name and description</li>
    <li>Observed activity before, during, after rule triggered</li>
    <li>Supporting evidence from tools, threat intel, or prior tickets</li>
    <li>Links to session timelines, incident event URL, search queries, and raw logs analyzed</li>
    <li>ADD analyst discretion context for triage, escalation, or reporting</li>
  </ul>
</li>
<li><strong>SAVE</strong> the case note</li>
</ol>

<h3>2.5 First Major Checkpoint - Artifact Assessment</h3>

<p><strong>EVALUATE the primary artifact using this decision tree:</strong></p>

<p><strong>QUESTION 1: Does this artifact match a known benign pattern/activity?</strong></p>
<ul>
<li><strong>CHECK</strong> Client Knowledge Base for the specific artifact/process/activity</li>
<li><strong>IF YES</strong> → Proceed to 2.6 (Benign closure)</li>
<li><strong>IF NO</strong> → Continue to Question 2</li>
<li><strong>EXAMPLE:</strong> First activity alerts for new hire based on analysis finding and documenting first seen date as relatively recent and user risk trend showing little to no activity until onboarded</li>
</ul>

<p><strong>QUESTION 2: Is this identical to a previously investigated incident?</strong></p>
<ul>
<li><strong>SEARCH</strong> recent tickets for same entity OR entity type (i.e. same type of users, assets) + same primary risk reason</li>
<li><strong>IF YES</strong> → Proceed to 2.7 (Duplicate closure)</li>
<li><strong>IF NO</strong> → Continue to Question 3</li>
</ul>

<p><strong>QUESTION 3: Is this part of an ongoing escalated investigation?</strong></p>
<ul>
<li><strong>SEARCH</strong> for related tickets already escalated for same artifact type</li>
<li><strong>IF YES</strong> → Proceed to 2.8 (Already Escalated closure)</li>
<li><strong>IF NO</strong> → Proceed to Phase 3: Deep Investigation</li>
</ul>

<h3>2.6 CREATE Artifact Status Case Note - Benign</h3>
<ol>
<li><strong>CLICK</strong> "Add Note"</li>
<li><strong>TITLE:</strong> "Closure - Benign Activity"</li>
<li><strong>DOCUMENT:</strong><br/>
<pre>CONCLUSION: Benign
RATIONALE: [Specific reason - KB reference, client confirmation, etc.]
SUPPORTING EVIDENCE: [KB article, change request, etc.]
REFERENCE TICKETS: [Any related previous investigations]
DISPOSITION: Close as False Positive</pre>
</li>
<li><strong>SAVE</strong> and proceed to Phase 4: Case Closure</li>
</ol>

<h3>2.7 CREATE Artifact Status Case Note - Duplicate</h3>
<ol>
<li><strong>CLICK</strong> "Add Note"</li>
<li><strong>TITLE:</strong> "Closure - Duplicate Investigation"</li>
<li><strong>DOCUMENT:</strong><br/>
<pre>CONCLUSION: Duplicate
RATIONALE: Same entity and primary risk reason as previous investigation
REFERENCE TICKET: [Ticket number]
DISPOSITION: Close as Duplicate</pre>
</li>
<li><strong>SAVE</strong> and proceed to Phase 4: Case Closure</li>
</ol>

<h3>2.8 CREATE Artifact Status Case Note - Already Escalated</h3>
<ol>
<li><strong>CLICK</strong> "Add Note"</li>
<li><strong>TITLE:</strong> "Closure - Already Under Investigation"</li>
<li><strong>DOCUMENT:</strong><br/>
<pre>CONCLUSION: Already Escalated
RATIONALE: Same artifact/pattern currently under Tier 2 review
REFERENCE TICKET: [Escalated ticket number]
DISPOSITION: Close as Already Escalated</pre>
</li>
<li><strong>SAVE</strong> and proceed to Phase 4: Case Closure</li>
</ol>

<hr />

<h2>Phase 3: Deep Investigation (Only if Phase 2 checkpoints failed)</h2>

<h3>3.1 Timeline Deep-Dive</h3>
<ol>
<li><strong>RETURN</strong> to the Incident Timeline page</li>
<li><strong>CONDUCT</strong> deep analysis for each primary risk reason or primary driver of incident:
  <ul>
    <li><strong>CLICK</strong> "Event Details" to view raw log data</li>
    <li><strong>CLICK</strong> "Data Insights" to review rule expression and historical patterns</li>
    <li><strong>REVIEW</strong> events preceding and succeeding to understand sequence</li>
    <li><strong>ANALYZE</strong> why this rule triggered, what led to it, and what happened after</li>
    <li><strong>DETERMINE</strong> if this indicates malicious activity, benign behavior, or suspicious patterns</li>
  </ul>
</li>
<li><strong>CREATE</strong> case note titled "Timeline Analysis"</li>
<li><strong>DOCUMENT</strong> key events, artifacts, and findings from timeline deep dive</li>
<li><strong>INCLUDE</strong> all session timeline URLs reviewed</li>
<li><strong>LEVERAGE</strong> additional investigation tools when necessary to aid in analysis</li>
</ol>

<h3>3.2 Threat Hunter Correlation</h3>
<ol>
<li><strong>CLICK</strong> triangle icon in search box → <strong>SELECT</strong> "Threat Hunter"</li>
<li><strong>ENTER</strong> search criteria for similar incidents in last 7 days</li>
<li><strong>EXECUTE</strong> search</li>
<li><strong>CREATE</strong> case note titled "Threat Hunter Results"</li>
<li><strong>DOCUMENT:</strong><br/>
<pre>Search Query: [Exact search parameters used]
Results: [Number of results and summary]
Relevant Findings: [Any correlations discovered]
Search URL: [If available]</pre>
</li>
</ol>

<h3>3.3 External Intelligence Check</h3>
<ol>
<li><strong>EXTRACT</strong> any external IPs/domains/hashes from timeline</li>
<li><strong>CHECK</strong> each indicator via VirusTotal, AlienVault, or other OSINT tools</li>
<li><strong>CREATE</strong> case note titled "OSINT Results"</li>
<li><strong>DOCUMENT:</strong><br/>
<pre>[Indicator] checked via [tool]
Result: [Clean/Malicious/Suspicious]
URL: [Direct link to results]
Additional Context: [Any relevant threat intel]</pre>
</li>
</ol>

<h3>3.4 CrowdStrike Investigation (If Applicable)</h3>
<p><strong>IF</strong> CrowdStrike access is available and relevant to investigation:</p>
<ol>
<li><strong>SEARCH</strong> for related artifacts, processes, or IOCs</li>
<li><strong>CREATE</strong> case note titled "CrowdStrike Investigation"</li>
<li><strong>DOCUMENT:</strong><br/>
<pre>CrowdStrike Query: [Search parameters]
Results: [Findings or "No additional artifacts found"]
Analysis: [Relevance to current investigation]</pre>
</li>
</ol>

<h3>3.5 Final Assessment</h3>
<ol>
<li><strong>CREATE</strong> case note titled "Investigation Conclusion"</li>
<li><strong>CHOOSE</strong> disposition:
  <ul>
    <li><strong>ESCALATE</strong> if suspicious activity confirmed</li>
    <li><strong>CLOSE</strong> if additional context reveals benign activity</li>
  </ul>
</li>
<li><strong>DOCUMENT</strong> final assessment:
  <ul>
    <li><strong>Benign</strong> – explain why, with supporting evidence</li>
    <li><strong>Not Benign / True Positive</strong> – explain what is suspicious or malicious, with supporting evidence</li>
    <li><strong>False Positive</strong> – explain why it was incorrectly triggered</li>
    <li><strong>Requires Escalation</strong> – justify escalation with evidence</li>
  </ul>
</li>
</ol>

<hr />

<h2>Phase 4: Case Closure &amp; Communication Requirements</h2>

<h3>4.1 Update Incident Description</h3>
<ol>
<li><strong>CLICK</strong> main incident description field</li>
<li><strong>REPLACE</strong> with comprehensive summary: "[Disposition] - [Primary artifact] - [Context summary] - [Key findings] - [Rationale]"</li>
<li><strong>EXAMPLE:</strong> "False Positive - First application login - New employee onboarding - Analysis confirmed recent hire date 2024-01-15 with no prior activity history - Standard onboarding pattern"</li>
<li><strong>SAVE</strong> changes</li>
</ol>

<h3>4.2 Escalation Communication Requirements</h3>

<ac:structured-macro ac:name="warning" ac:schema-version="1">
  <ac:rich-text-body>
    <p><strong>IF setting status to "GT Review":</strong></p>
    <ul>
      <li><strong>SEND</strong> immediate chat message to Sangamithirai</li>
      <li><strong>MESSAGE:</strong> "Ticket [number] escalated to GT Review - [brief reason]"</li>
      <li><strong>DO NOT</strong> mark GT Review emails as read in GTCyberMSS</li>
      <li><strong>WAIT</strong> 30 minutes for response</li>
    </ul>
    <p><strong>IF no response within 30 minutes:</strong></p>
    <ul>
      <li><strong>SEND</strong> email to: Sangamithirai, Sivakrishna, Ahmed, John Pearce, Kabir Advani</li>
      <li><strong>SUBJECT:</strong> "Urgent: GT Review ticket [number] requires attention"</li>
      <li><strong>INCLUDE</strong> brief summary and escalation reason</li>
    </ul>
  </ac:rich-text-body>
</ac:structured-macro>

<h3>4.3 Incident Documentation Channel Posting</h3>
<p><strong>IF</strong> incident requires clarification or potential client escalation:</p>
<ol>
<li><strong>CREATE</strong> post in KC3 Team Incident Documentation Channel</li>
<li><strong>TITLE:</strong> "Incident [number] - [Entity] - [Primary artifact]"</li>
<li><strong>INCLUDE:</strong>
  <ul>
    <li>Brief incident summary</li>
    <li>Key findings</li>
    <li>Specific questions or concerns</li>
    <li>Request for guidance</li>
  </ul>
</li>
</ol>

<h3>4.4 Set Final Status</h3>
<ol>
<li><strong>CLICK</strong> Status dropdown</li>
<li><strong>SELECT</strong> appropriate closure status:
  <ul>
    <li>"Closed" (for benign/false positive/duplicate)</li>
    <li>"GT Review" (for escalation - follow communication requirements in 4.2)</li>
  </ul>
</li>
<li><strong>VERIFY</strong> all case notes are present and complete</li>
</ol>

<h3>4.5 Mandatory Verification Checklist</h3>

<ac:structured-macro ac:name="info" ac:schema-version="1">
  <ac:rich-text-body>
    <p><strong>VERIFY each item before final submission:</strong></p>
    <ul>
      <li>☐ Entity Information case note created with timeline links</li>
      <li>☐ Risk Score case note created with incident event URL</li>
      <li>☐ Risk Reasons case note created</li>
      <li>☐ Primary Risk Analysis case note created</li>
      <li>☐ Timeline Analysis case note created (if deep investigation conducted)</li>
      <li>☐ Threat Hunter Results documented with search queries (if used)</li>
      <li>☐ OSINT Results documented with URLs (if used)</li>
      <li>☐ CrowdStrike investigation noted (if applicable, even if no findings)</li>
      <li>☐ Closure rationale case note created</li>
      <li>☐ Incident description updated with comprehensive summary</li>
      <li>☐ Status changed to final disposition</li>
      <li>☐ Escalation communications completed (if GT Review)</li>
      <li>☐ DO NOT DELETE any existing comments - update/add context only</li>
    </ul>
  </ac:rich-text-body>
</ac:structured-macro>

<h3>4.6 Comment Management</h3>
<ul>
<li><strong>NEVER</strong> delete existing comments in tickets</li>
<li><strong>UPDATE</strong> comments by adding context, corrections, or additional information</li>
<li><strong>USE</strong> format: "[Date] [Your Name] - UPDATE: [additional context]"</li>
</ul>

<hr />

<ac:structured-macro ac:name="info" ac:schema-version="1">
  <ac:rich-text-body>
    <p><strong>Document Approval</strong></p>
    <p>This playbook incorporates all management requirements while maintaining sequential, imperative structure for consistent execution.</p>
  </ac:rich-text-body>
</ac:structured-macro>
"""

    # Create the page as DRAFT
    payload = {
        'type': 'page',
        'title': title,
        'space': {'key': space_key},
        'status': 'draft',  # Create as draft
        'body': {
            'storage': {
                'value': html,
                'representation': 'storage'
            }
        }
    }

    if parent_id:
        payload['ancestors'] = [{'id': parent_id}]

    response = requests.post(url, auth=auth, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        page = response.json()
        print(f"\n✓ DRAFT SOP created successfully!")
        print(f"  Title: {title}")
        print(f"  Status: DRAFT (not published)")
        print(f"  URL: {base_url}/wiki{page['_links']['webui']}")
        print(f"\n  You can review and publish it from Confluence when ready.")
        return page
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.text)
        return None


def main():
    print("=" * 70)
    print("Exabeam Incident Response Playbook - Confluence SOP Creator")
    print("=" * 70)
    print()

    # Get credentials
    email = input("Your Atlassian email: ").strip()
    api_token = input("Your API token: ").strip()

    print()
    space_key = input("Space key [MDS]: ").strip() or 'MDS'
    parent_id = input("Parent page ID (optional, press Enter to skip): ").strip() or None

    print("\nCreating SOP page...")
    create_exabeam_sop(
        base_url='https://grantthorntonsupport.atlassian.net',
        email=email,
        api_token=api_token,
        space_key=space_key,
        parent_id=parent_id
    )


if __name__ == '__main__':
    main()
