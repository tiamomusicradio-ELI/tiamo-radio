import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { collection, doc, getDoc, getDocs } from "firebase/firestore";
import { db, realtimeDB, ref } from './firebase.tsx';
import { onValue } from "firebase/database";

import './board.css';

import backIcon from './back.png';

function Board() {
    const [schedule, setSchedule] = useState([]);
    const [isSchedule, setIsSchedule] = useState(true); 
    const [noScheduleMessage, setNoScheduleMessage] = useState("אין שידורים"); 

    useEffect(() => {
        // קריאה לערך isSchedule מ-Realtime Database
        const isScheduleRef = ref(realtimeDB, "isSchedule");
        const unsubscribeIsSchedule = onValue(isScheduleRef, (snapshot) => {
            if (snapshot.exists()) {
                setIsSchedule(snapshot.val());
            }
        });

        // קריאה לנתוני לוח השידורים מ-Firestore
        const fetchSchedule = async () => {
            try {
                const querySnapshot = await getDocs(collection(db, "schedule"));
                const data = querySnapshot.docs.map(doc => ({
                    time: doc.data().time,
                    program: doc.data().value,
                    index: doc.data().index
                }));
                const sort_data = data.sort((a,b) => a.index - b.index)
                setSchedule(sort_data);
            } catch (error) {
                console.error("Error fetching schedule:", error);
            }
        };

        // קריאה להודעה מתוך settings
        const fetchNoScheduleMessage = async () => {
            try {
                const docRef = doc(db, "settings", "message");
                const docSnap = await getDoc(docRef);

                if (docSnap.exists()) {
                    setNoScheduleMessage(docSnap.data().value);
                }
            } catch (error) {
                console.error("Error fetching no schedule message:", error);
            }
        };

        fetchSchedule();
        fetchNoScheduleMessage();

        // ניקוי המאזין כאשר הקומפוננטה יוצאת מהמסך
        return () => {
            unsubscribeIsSchedule();
        };
    }, []);

    const BackButton = () => {
        return <Link to="/"><img className="back_button" src={backIcon} alt="Back"/></Link>;
    };

    const Schedule = () => {
        return (
            <div className="schedule">
                <div className="title">לוח שידורים</div>
                {isSchedule ? (
                    <div className="description" style={{}}>
            <span>
                 {/* className="script"> */}
                    <table border="1">
                        <thead>
                            <tr>
                                <th>שעה</th>
                                <th>תוכנית</th>
                            </tr>
                        </thead>
                        <tbody>
                            {schedule.map((item, index) => (
                                <tr key={index}>
                                    <td>{item.time}</td>
                                    <td>{item.program}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    </span>
                    </div>
                ) : (
                    <div className="subtitle">{noScheduleMessage}</div>
                )}
            </div>
        );
    };

    return (
        <div className="board_container">
            <Schedule />
            <BackButton />
        </div>
    );
}

export default Board;
