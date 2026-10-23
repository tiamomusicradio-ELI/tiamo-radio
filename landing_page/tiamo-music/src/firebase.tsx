// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getDatabase, ref } from "firebase/database";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDOX0um0CbwwDHoImxZxsWEOo9BIVtlXyE",
  authDomain: "tiamo-music-radio.firebaseapp.com",
  databaseURL: "https://tiamo-music-radio-default-rtdb.firebaseio.com",
  projectId: "tiamo-music-radio",
  storageBucket: "tiamo-music-radio.firebasestorage.app",
  messagingSenderId: "956733278301",
  appId: "1:956733278301:web:6ed1e355e7613fa3f0a5b4"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const realtimeDB = getDatabase(app);

export { db, realtimeDB, ref };