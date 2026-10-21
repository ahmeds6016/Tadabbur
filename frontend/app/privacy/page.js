import Link from 'next/link';

export const metadata = { title: 'Privacy notice | Tadabbur' };

const CONTACT = 'ahmedsheik123@gmail.com';

export default function PrivacyPage() {
  return <main className="container"><article className="card" style={{ lineHeight: 1.7 }}>
    <h1>Privacy notice</h1>
    <p>Last updated October 21, 2026. This notice explains what Tadabbur stores, how it is used and how to remove it.</p>
    <h2>Information collected</h2>
    <p>Firebase Authentication manages your email, password-based sign-in, display name and session information. Tadabbur stores your profile and learning preferences, verse history, saved answer snapshots and folders, reflections and highlights, tags, linked verses, study progress, streaks, badges, collections and reading plans.</p>
    <p>The private journal feature is currently switched off. If it is enabled in future, it can hold behavior logs, heart notes, declared struggles, goals and the summaries, insights and narratives derived from them. Feedback you send includes your account ID, email, message and an edited summary.</p>
    <h2>How processing works</h2>
    <p>Tadabbur uses Google Cloud Vertex AI to prepare explanations from canonical verse references, classical source excerpts and learning preferences. Shared tafsir requests do not include your free-text verse request. Topic discovery may process the text you enter. Feedback may be processed to prepare a summary. If the private journal is enabled, its relevant notes and derived context may be sent to Vertex AI when generating guidance or summaries. Google does not use these requests to train its models; it may keep request data for a limited time for caching and abuse monitoring under the Google Cloud terms.</p>
    <p>Private reflections are never sent with tafsir requests. Account and content data are stored in Firebase Authentication and two Google Cloud Firestore databases. Scripture and classical source texts are stored separately. Google reCAPTCHA checks sign-in and account creation for automated abuse. Feedback is stored in the application database and is not currently sent to other services; copies made by earlier versions are removed on request.</p>
    <h2>Storage and retention</h2>
    <p>Profile, reflections, history and saved answers have no automatic retention period. They remain until you delete them or your account. Shared answer cache records are removed after 90 days, although removal can be delayed by up to a few days.</p>
    <p>Reflection text and highlighted passages are encrypted by the application before they are stored. Browser storage holds your Firebase sign-in and onboarding preferences. Session storage keeps your most recent answer for up to 30 minutes, for the signed-in account that viewed it, until the tab closes.</p>
    <p>Operational logs record request identifiers, status and canonical verse references, not the text of your reflections. Google Cloud request logs include IP address and browser details. Both are kept for 30 days. Database recovery copies include seven days of point-in-time history and daily backups kept for 14 days for account data and seven days for the shared verse and answer database. Deleting data removes it from active storage immediately; recovery copies expire on that schedule.</p>
    <h2>Account deletion</h2>
    <p>Settings offers account deletion after a fresh password confirmation. The process deletes your profile and all of your stored records, including any private journal records and feedback linked to your account. It removes your sign-in account last and clears account data from the browser. A minimal deletion record, keyed by a one-way hash of your account ID, is kept so that interrupted deletions can resume and late requests are refused. It is removed automatically 30 days after deletion completes.</p>
    <p>Public share links contain only the verse explanation and no account details, so they stay available after account deletion. To remove a link you created, send it to the contact address below.</p>
    <h2>Contact and choices</h2>
    <p>You can browse as a guest, edit your learning profile, delete individual reflections or saved answers, and delete your account in Settings. For access, correction, deletion questions or share link removal, contact <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.</p>
    <p><Link href="/settings">Settings</Link> · <Link href="/">Return to Tadabbur</Link></p>
  </article></main>;
}
