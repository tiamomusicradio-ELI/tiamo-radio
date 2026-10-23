import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { collection, getDocs } from "firebase/firestore";
import { db, realtimeDB, ref } from './firebase.tsx';
import { onValue } from "firebase/database";

import './home.css';

import onairIcon from './onair.png';
import playControlIcon from './play.png';
import stopControlIcon from './stop.png';
import waveIcon from './waves.gif';
import facebookIcon from './facebook-icon.png';
import akomIcon from './akom-icon.jpg';
import whatsappIcon from './whatsapp-icon.png';
import mailIcon from './email-icon.png';

let phoneNumber = "972538550511"; 

const FACEBOOK_URL = 'https://www.facebook.com/share/13pcuF7EMx/';
const WATHSAPP_URL = `https://wa.me/${phoneNumber}`;
const MAIL_URL = 'mailto:tiamo.music.radio@gmail.com';

function Home(props: { setPlay: any, isControl: any }) {
    const [isOnAir, setOnAir] = useState(true);
    const [isDedicated, setDedicated] = useState(true);
    const [schedule, setSchedule] = useState<any[]>([]);
    const [dedicatedMessages, setDedicatedMessages] = useState<string[]>([]);

    // ================= realtime listeners =================
    useEffect(() => {
        const onAirRef = ref(realtimeDB, "onair");
        const unsubscribeOnAir = onValue(onAirRef, (snapshot) => {
            if (snapshot.exists()) {
                setOnAir(snapshot.val());
            }
        });

        const dedicatedRef = ref(realtimeDB, "dedicated");
        const unsubscribeDedicated = onValue(dedicatedRef, (snapshot) => {
            if (snapshot.exists()) {
                setDedicated(snapshot.val());
            }
        });

        const dedicatedMessagesRef = ref(realtimeDB, "all_dedicated");
        const unsubscribeDedicatedMessages = onValue(dedicatedMessagesRef, (snapshot) => {
            if (snapshot.exists()) {
                setDedicatedMessages(
                    Object.values(snapshot.val()).map((item: any) => item.text)
                );
            } else {
                setDedicatedMessages([]);
            }
        });

        return () => {
            unsubscribeOnAir();
            unsubscribeDedicated();
            unsubscribeDedicatedMessages();
        };
    }, []);

    // ================= fetch schedule =================
    useEffect(() => {
        const fetchSchedule = async () => {
            try {
                const querySnapshot = await getDocs(collection(db, "schedule"));
                const data = querySnapshot.docs.map(doc => ({
                    time: doc.data().time,
                    program: doc.data().value,
                    index: doc.data().index
                }));

                // חשוב: מיון לפי index
                data.sort((a, b) => a.index - b.index);

                setSchedule(data);
            } catch (error) {
                console.error("Error fetching schedule:", error);
            }
        };

        fetchSchedule();
    }, []);

    const handleControl = () => {
        props.setPlay((c: boolean) => !c);
    };

    // ================= חישוב מה מתנגן עכשיו =================
    const getCurrentProgram = () => {
        const now = new Date();
        const currentMinutes = now.getHours() * 60 + now.getMinutes();

        for (let item of schedule) {
            if (!item.time) continue;

            const [start, end] = item.time.split("-");
            if (!start || !end) continue;

            const [sh, sm] = start.split(":").map(Number);
            const [eh, em] = end.split(":").map(Number);

            const startMinutes = sh * 60 + sm;
            const endMinutes = eh * 60 + em;

            if (currentMinutes >= startMinutes && currentMinutes <= endMinutes) {
                return {program: item.program, time: item.time};
            }
        }

        return "לא נמצא שידור כרגע";
    };

    const Control = () => {
        return (
            <div className="control">
                <img
                    src={props.isControl ? stopControlIcon : playControlIcon}
                    className="play"
                    onClick={handleControl}
                />
                <img src={waveIcon} className="wave" />
            </div>
        );
    };

    const Links = () => {
        return (
            <div className="links">
                <Link to="/about">
                    <div className="button">אודות התחנה</div>
                </Link>
                <Link to="/request">
                    <div className="button">בא לי לשמוע</div>
                </Link>
                <Link to="/board">
                    <div className="button">לוח שידורים</div>
                </Link>
            </div>
        );
    };

    const Social = () => {
        return (
            <div className="social">
                            <div className="subtitle">מוזיקה באווירה אחרת</div>
                <a href={MAIL_URL}>
                    <img src={mailIcon} className="button" />
                </a>
                <a href={WATHSAPP_URL} target="_blank" rel="noreferrer">
                    <img src={whatsappIcon} className="button" />
                </a>
                <a href={FACEBOOK_URL} target="_blank" rel="noreferrer">
                    <img src={facebookIcon} className="button" />
                </a>
                <img src={akomIcon} className="button" />
            </div>
        );
    };

    const Dedicated = () => {
        return (
            <div className="dedicated" style={{ display: isDedicated ? '' : 'none' }}>
                <p className="marquee">
                    <span className="script">
                        {dedicatedMessages.map((value, index) => (
                            <span key={index} className="text">{value}</span>
                        ))}
                    </span>
                </p>
            </div>
        );
    };

    const date = new Date();

    return (
        <div>
            <div className="date">
                {`${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`}
            </div>

            <img
                src={onairIcon}
                className="onair enable"
                style={{ display: isOnAir ? '' : 'none' }}
            />

            <div className="title">TIAMO MUSIC</div>

            <Control />

            <div className="heresing">
                👆
                <div className="text">להאזנה לחץ עלי</div>
            </div>

            <div className="subtitle">
            {`אתם מאזינים לתוכנית`}
            <br />
            {getCurrentProgram().program || 'שידור לא ידוע'}
            </div> 
                   <div className="subtitle">{getCurrentProgram().time}</div>

            <Links />
            <Social />
            <Dedicated />
        </div>
    );
}

export default Home;