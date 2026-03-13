// ---------- app.js ----------
// Replace the config below with YOUR Firebase project's config (from Firebase console)
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "SENDER_ID",
  appId: "APP_ID"
};

// initialize (compat style)
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();

/* ---------- AUTH & COMMON ---------- */

// sign out helper
function signOutUser() {
  auth.signOut().then(()=> {
    window.location = 'index.html';
  });
}

// on login state change — simple role redirect helper for pages that aren't full apps
auth.onAuthStateChanged(async (user) => {
  // nothing here — pages call init functions which will check user status
});

/* ---------- USER PAGE API ---------- */

/**
 * initPageForUser(callback)
 * callback receives an array of helpers [{ id, name, service, rate, address, bio }]
 */
async function initPageForUser(onHelpersLoaded) {
  // ensure user logged in; if not redirect to login
  auth.onAuthStateChanged(async (user) => {
    if (!user) {
      // not logged in — go to login
      // but you might want visitors to browse without login — change if needed
      // window.location = 'login.html';
      // For demo we'll allow browsing without login:
    }
    // Load helpers from Firestore
    try {
      const snapshot = await db.collection('helpers').get();
      const helpers = snapshot.docs.map(d => {
        const dt = d.data();
        return {
          id: d.id,
          name: dt.name || dt.userEmail || 'Helper',
          service: dt.service || (dt.services ? dt.services.split(',')[0] : 'Service'),
          rate: dt.rate || dt.ratePerHour || 0,
          address: dt.address || '',
          bio: dt.bio || ''
        };
      });
      onHelpersLoaded && onHelpersLoaded(helpers);
    } catch (err) {
      console.error('Failed to load helpers', err);
      onHelpersLoaded && onHelpersLoaded([]);
    }
  });
}

/**
 * createBooking(helperId, service, isoDateTime, hours, rate)
 * Saves booking with current logged-in user as seeker (if logged in), else saves guest booking with null userId
 */
async function createBooking(helperId, service, isoDateTime, hours, rate) {
  const user = auth.currentUser;
  const seekerId = user ? user.uid : null;
  const seekerName = user ? (user.displayName || user.email) : 'Guest';
  const total = Number(rate) * Number(hours);
  const payload = {
    helperId,
    service,
    start_time: new Date(isoDateTime).toISOString(),
    hours,
    total_amount: total,
    status: 'pending',
    seekerId,
    seekerName,
    created_at: new Date().toISOString()
  };
  const docRef = await db.collection('bookings').add(payload);
  return docRef.id;
}

/* ---------- HELPER PAGE API ---------- */

/**
 * saveHelperProfile(profile)
 * profile: { name, services (string), rate, address, bio }
 * Associates profile with currently logged-in user (uid)
 */
async function saveHelperProfile(profile) {
  const user = auth.currentUser;
  if (!user) throw new Error('You must be logged in as helper to save profile');

  // Save in 'helpers' collection with doc id = user.uid for easy lookup
  await db.collection('helpers').doc(user.uid).set({
    name: profile.name,
    services: profile.services,
    service: (profile.services||'').split(',')[0].trim(),
    rate: profile.rate,
    address: profile.address,
    bio: profile.bio || '',
    userEmail: user.email,
    updated_at: new Date().toISOString()
  }, { merge: true });

  // Also ensure user record in 'users' collection has role helper
  await db.collection('users').doc(user.uid).set({
    name: profile.name,
    role: 'helper',
    email: user.email
  }, { merge: true });
}

/**
 * initPageForHelper(hooks)
 * hooks: { onProfileLoaded(profile), onBookingsLoaded(bookings) }
 */
function initPageForHelper(hooks) {
  auth.onAuthStateChanged(async (user) => {
    if (!user) {
      window.location = 'login.html';
      return;
    }
    // Load helper profile (doc id = user.uid)
    const doc = await db.collection('helpers').doc(user.uid).get();
    const profile = doc.exists ? doc.data() : null;
    hooks.onProfileLoaded && hooks.onProfileLoaded(profile);

    // Load bookings where helperId == user.uid
    const snap = await db.collection('bookings').where('helperId','==', user.uid).get();
    const bookings = snap.docs.map(d => {
      const x = d.data();
      return {
        id: d.id,
        service: x.service,
        hours: x.hours,
        start_time: x.start_time,
        status: x.status,
        userName: x.seekerName || 'User'
      };
    });
    hooks.onBookingsLoaded && hooks.onBookingsLoaded(bookings);
  });
}

/* ---------- OPTIONAL: generic init for pages that need to know user role ---------- */

/**
 * loadCurrentUserRole()
 * returns user's role from users collection (if exists)
 */
async function loadCurrentUserRole() {
  const user = auth.currentUser;
  if (!user) return null;
  const doc = await db.collection('users').doc(user.uid).get();
  if (!doc.exists) return null;
  return doc.data().role || null;
}

/* Dummy helpers with service categories */
const helpers = [
  {
    id: 1,
    name: "Ramesh Sharma",
    service: "Grocery",
    rate: 200,
    address: "Kothrud, Pune",
    bio: "Friendly and punctual. I help with groceries and errands.",
    rating: 4.5,
    image: "https://randomuser.me/api/portraits/men/75.jpg"
  },
  {
    id: 2,
    name: "Seema Desai",
    service: "Cleaning",
    rate: 300,
    address: "Andheri, Mumbai",
    bio: "I provide cleaning and laundry services with care.",
    rating: 4.8,
    image: "https://randomuser.me/api/portraits/women/65.jpg"
  },
  {
    id: 3,
    name: "Vikas Patil",
    service: "Laundry",
    rate: 250,
    address: "Baner, Pune",
    bio: "Experienced in laundry and clothes care.",
    rating: 4.2,
    image: "https://randomuser.me/api/portraits/men/41.jpg"
  },
  {
    id: 4,
    name: "Anjali Mehta",
    service: "Personal Care",
    rate: 400,
    address: "Borivali, Mumbai",
    bio: "Skilled in elder personal care and hygiene assistance.",
    rating: 5,
    image: "https://randomuser.me/api/portraits/women/72.jpg"
  }
];

/* ---------- USER DASHBOARD ---------- */
if (document.getElementById("helpersRow")) {
  const container = document.getElementById("helpersRow");
  const search = document.getElementById("searchInput");
  const tabs = document.querySelectorAll("#serviceTabs .nav-link");

  function renderHelpers(list) {
    container.innerHTML = "";
    if (list.length === 0) {
      container.innerHTML = `<p class="text-center text-muted">No helpers found.</p>`;
      return;
    }
    list.forEach(h => {
      const card = document.createElement("div");
      card.className = "col-md-4";
      card.innerHTML = `
        <div class="helper-card shadow-sm h-100">
          <img src="${h.image}" class="helper-photo" alt="${h.name}">
          <h5>${h.name}</h5>
          <p class="mb-1"><b>${h.service}</b> — ₹${h.rate}/hr</p>
          <p class="text-muted small mb-1">${h.address}</p>
          <div class="rating mb-2">⭐ ${h.rating}/5</div>
          <p class="small">${h.bio}</p>
        </div>`;
      container.appendChild(card);
    });
  }

  // Default load
  renderHelpers(helpers);

  // Search filter
  search.addEventListener("input", () => {
    const q = search.value.toLowerCase();
    const filtered = helpers.filter(h =>
      h.name.toLowerCase().includes(q) ||
      h.address.toLowerCase().includes(q)
    );
    renderHelpers(filtered);
  });

  // Tab filter
  tabs.forEach(tab => {
    tab.addEventListener("click", e => {
      e.preventDefault();
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const selected = tab.dataset.service;
      if (selected === "all") renderHelpers(helpers);
      else renderHelpers(helpers.filter(h => h.service === selected));
    });
  });
}

/* ---------- HELPER DASHBOARD ---------- */
if (document.getElementById("helperImage")) {
  const fileInput = document.getElementById("helperImage");
  const preview = document.getElementById("helperImagePreview");

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) preview.src = URL.createObjectURL(file);
  });

  document.getElementById("saveProfileBtn").addEventListener("click", () => {
    const name = document.getElementById("helperName").value;
    const service = document.getElementById("helperService").value;
    const rate = document.getElementById("helperRate").value;
    const address = document.getElementById("helperAddress").value;
    const bio = document.getElementById("helperBio").value;
    alert(`Profile Saved ✅\n\nName: ${name}\nService: ${service}\nRate: ₹${rate}/hr\nAddress: ${address}\nBio: ${bio}`);
  });
}





/* ---------- small security note / helper functions ---------- */
// Note: This is a simple demo-friendly app.js. For a production app:
// - Use security rules in Firestore to enforce role-based reads/writes
// - Validate and sanitize all inputs on server side or Cloud Functions
// - Use Firebase Storage rules for uploads

// END of app.js
