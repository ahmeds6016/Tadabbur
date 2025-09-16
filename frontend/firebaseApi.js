import axios from "https://cdn.jsdelivr.net/npm/axios@1.7.2/dist/axios.min.js";

const API_BASE = "https://tafsir-backend-612616741510.us-central1.run.app";

export const setUserProfile = async (idToken, level) => {
  try {
    const res = await axios.post(
      `${API_BASE}/set_profile`,
      { level },
      { headers: { Authorization: `Bearer ${idToken}` } }
    );
    return res.data;
  } catch (err) {
    console.error("Error setting profile:", err.response?.data || err.message);
    throw err;
  }
};

export const getTafsir = async (idToken, query) => {
  try {
    const res = await axios.post(
      `${API_BASE}/tafsir`,
      { query },
      { headers: { Authorization: `Bearer ${idToken}` } }
    );
    return res.data;
  } catch (err) {
    console.error("Error getting tafsir:", err.response?.data || err.message);
    throw err;
  }
};
