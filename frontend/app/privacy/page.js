import Link from 'next/link';

export const metadata = { title: 'Privacy notice draft | Tadabbur' };

export default function PrivacyPage() {
  return <main className="container"><article className="card" style={{ lineHeight: 1.7 }}>
    <h1>Privacy notice — draft for owner review</h1>
    <p>This draft describes the application code as of October 20, 2026. Ahmed must review the contact details, provider retention and public-share policy before publication.</p>
    <h2>Information collected</h2>
    <p>Firebase Authentication manages your email, password-based sign-in, display name and session information. Tadabbur stores your profile and learning preferences, verse history, saved answer snapshots and folders, reflections and highlights, tags, linked verses, study progress, streaks, badges, collections and reading plans.</p>
    <p>The suspended private journal can contain behavior logs, heart notes, declared struggles, goals and derived summaries, insights and narratives. Its routes are disabled unless explicitly enabled. Feedback can include your account ID, email, message and an edited summary.</p>
    <h2>How processing works</h2>
    <p>Tadabbur uses Google Cloud Vertex AI to prepare explanations from canonical verse references, classical source excerpts and learning preferences. Shared tafsir prompts do not include your free-text verse request. Topic discovery may process the text you enter. Feedback may be processed to prepare a summary. If the private journal is enabled, its relevant notes and derived context may be sent to Vertex AI when generating guidance or summaries.</p>
    <p>Private reflections are not sent with ordinary shared tafsir requests. Account and content data are stored in Firebase Authentication and two Google Cloud Firestore databases. Public scripture and classical source files are stored separately in Firestore and Cloud Storage. Optional GitHub issue and email integrations can export feedback. Their activation and the handling of existing external copies require owner review.</p>
    <h2>Storage and retention</h2>
    <p>Profile, reflections, history, saved answers and journal records have no automatic application retention period. They remain until deleted. Shared answer cache records have a 90-day Firestore TTL policy; removal can be delayed. Public shared snapshots currently have no expiry or revocation route.</p>
    <p>Reflection text uses application encryption when the server encryption secret is configured. Legacy plaintext remains readable and requires a separate migration. This draft does not claim every historical record is encrypted. Browser storage includes Firebase sign-in persistence, onboarding preferences and a recent answer cached in session storage for up to 30 minutes.</p>
    <p>Operational logs record request identifiers, status and canonical references. Infrastructure log retention and provider processing retention: [Ahmed to confirm]. Database recovery includes seven days of point-in-time history and daily backups retained for 14 days in the user database and seven days in the corpus/cache database. Deletion from active storage does not immediately erase those recovery copies.</p>
    <h2>Account deletion</h2>
    <p>Settings requires a fresh password confirmation before account deletion. The resumable process deletes all user-document descendants, including every private journal collection, and account-linked feedback in the application database. It removes the sign-in account last and clears account browser state. A minimal deletion status record, keyed by a hash of the account ID, remains to prevent late writes and allow retries. Its retention and cleanup policy: [Ahmed to confirm].</p>
    <p>Public shares have no creator account field today. Account deletion therefore cannot identify which public snapshots you created. The policy for retaining or removing these snapshots is unresolved and must be reviewed before publication. Existing exports to GitHub or email and historical operational logs need separate review; deleting the application account does not automatically erase those copies.</p>
    <h2>Contact and choices</h2>
    <p>You can browse as a guest, edit your learning profile, delete individual reflections or saved answers, and request account deletion in Settings. Contact for access, correction, deletion questions and public-share requests: [Ahmed to confirm].</p>
    <p><Link href="/settings">Settings</Link> · <Link href="/">Return to Tadabbur</Link></p>
  </article></main>;
}
