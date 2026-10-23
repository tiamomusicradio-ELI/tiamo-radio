import React, { useState, useEffect } from 'react';
import { collection, doc, getDoc, getDocs, setDoc, deleteDoc, addDoc } from "firebase/firestore";
import { db, realtimeDB, ref } from './firebase.tsx';
import { onValue, set, push, remove, update } from "firebase/database";
import { Link } from 'react-router-dom';

import './board.css';
import backIcon from './back.png';

function Admin() {
    // State לניהול הנתונים
    const [schedule, setSchedule] = useState([]);
    const [isSchedule, setIsSchedule] = useState(true);
    const [isOnAir, setOnAir] = useState(true);
    const [isDedicated, setDedicated] = useState(true);
    const [noScheduleMessage, setNoScheduleMessage] = useState("אין שידורים");
    const [allDedicated, setAllDedicated] = useState([]);

    useEffect(() => {
        const isScheduleRef = ref(realtimeDB, "isSchedule");
        const unsubscribeIsSchedule = onValue(isScheduleRef, (snapshot) => {
            if (snapshot.exists()) {
                setIsSchedule(snapshot.val());
            }
        });

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

        // מאזין ל-all_dedicated
        const allDedicatedRef = ref(realtimeDB, "all_dedicated");
        const unsubscribeAllDedicated = onValue(allDedicatedRef, (snapshot) => {
            if (snapshot.exists()) {
                setAllDedicated(Object.entries(snapshot.val()).map(([key, value]) => ({
                    id: key,
                    text: value.text
                })));
            } else {
                setAllDedicated([]);
            }
        });

        // קריאה ללוח השידורים מ-Firestore
        const fetchSchedule = async () => {
            try {
                const querySnapshot = await getDocs(collection(db, "schedule"));
                const data = querySnapshot.docs.map(doc => ({
                    id: doc.id,
                    index: doc.data().index,
                    time: doc.data().time,
                    program: doc.data().value
                }));
                const sort_data = data.sort((a,b) => a.index - b.index)
                setSchedule(sort_data);
            } catch (error) {
                console.error("Error fetching schedule:", error);
            }
        };

        fetchSchedule();

        return () => {
            unsubscribeIsSchedule();
            unsubscribeOnAir();
            unsubscribeDedicated();
            unsubscribeAllDedicated();
        };
    }, []);

    // פונקציה לעדכון טוגל ב-Realtime Database
    const handleToggle = (dbPath, value) => {
        set(ref(realtimeDB, dbPath), value);
    };

    // פונקציות לניהול הודעת noScheduleMessage
    const handleSaveNoScheduleMessage = async () => {
        try {
            await setDoc(doc(db, "settings", "message"), { value: noScheduleMessage });
            alert("ההודעה נשמרה בהצלחה!");
        } catch (error) {
            console.error("Error saving no schedule message:", error);
        }
    };

    // פונקציות לניהול לוח השידורים
    const handleEditCell = (index, field, value) => {
        const updatedSchedule = [...schedule];
        updatedSchedule[index][field] = value;
        setSchedule(updatedSchedule);
    };

    const handleSaveChanges = async () => {
        try {
            await Promise.all(schedule.map(item => {
                return setDoc(doc(db, "schedule", item.id), {
                    time: item.time,
                    value: item.program,
                    index: item.index
                });
            }));
            alert("השינויים נשמרו בהצלחה!");
        } catch (error) {
            console.error("Error updating schedule:", error);
        }
    };

    const handleDeleteRow = async (id) => {
        try {
            await deleteDoc(doc(db, "schedule", id));
            setSchedule(schedule.filter(item => item.id !== id));
        } catch (error) {
            console.error("Error deleting schedule row:", error);
        }
    };

    const handleAddRow = async () => {
        try {
            const newDocRef = await addDoc(collection(db, "schedule"), {
                time: "00:00 - 00:00",
                value: "תוכנית חדשה",
                index: schedule.length
            });

            setSchedule([...schedule, { id: newDocRef.id, time: "00:00 - 00:00", program: "תוכנית חדשה" }]);
        } catch (error) {
            console.error("Error adding new row:", error);
        }
    };

    // פונקציות לניהול פס המסרים all_dedicated
    const handleAddDedicated = () => {
        const newDedicatedRef = push(ref(realtimeDB, "all_dedicated"));
        set(newDedicatedRef, { text: "הודעה חדשה" });
    };

    const handleEditDedicated = (id, newText) => {
        update(ref(realtimeDB, `all_dedicated/${id}`), { text: newText });
    };

    const handleDeleteDedicated = (id) => {
        remove(ref(realtimeDB, `all_dedicated/${id}`));
        setAllDedicated(allDedicated.filter(item => item.id !== id));
    };

    return (
        <div className="admin_container">
            <h2>ניהול התחנה</h2>

            <div className="toggles">
                <label>
                    הצגת ON AIR
                    <input type="checkbox" checked={isOnAir} onChange={() => handleToggle("onair", !isOnAir)} />
                </label><br />
                <label>
                    הצגת פס מסרים
                    <input type="checkbox" checked={isDedicated} onChange={() => handleToggle("dedicated", !isDedicated)} />
                </label><br />
                <label>
                    הצגת לוח שידורים או הודעה
                    <input type="checkbox" checked={isSchedule} onChange={() => handleToggle("isSchedule", !isSchedule)} />
                </label><br />
            </div>

            <div className="schedule">
                <label>הודעה ללא לוח שידורים</label>
                <input type="text" onChange={(e)=>setNoScheduleMessage(e.target.value)}/>
                <button onClick={()=>handleSaveNoScheduleMessage()}>שמור</button>
            </div>

            <div className="schedule">
                <h3>לוח שידורים</h3>
                <table border="1">
                    <thead>
                        <tr>
                            <th>שעה</th>
                            <th>תוכנית</th>
                            <th>פעולות</th>
                        </tr>
                    </thead>
                    <tbody>
                        {schedule.map((item, index) => (
                            <tr key={item.id}>
                                {/* <td><input type="text" value={item.index} onChange={(e) => handleEditCell(index, "index", e.target.value)} /></td> */}
                                <td><input type="text" value={item.time} onChange={(e) => handleEditCell(index, "time", e.target.value)} /></td>
                                <td><input type="text" value={item.program} onChange={(e) => handleEditCell(index, "program", e.target.value)} /></td>
                                <td><button onClick={() => handleDeleteRow(item.id)}>🗑 מחק</button></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                <button onClick={handleSaveChanges}>💾 שמור שינויים</button>
                <button onClick={handleAddRow}>➕ הוסף שורה</button>
            </div>

            <div className="dedicated-messages">
                <h3>פס מסרים</h3>
                <table border="1">
                    <thead>
                        <tr>
                            <th>תוכן</th>
                            <th>פעולות</th>
                        </tr>
                    </thead>
                    <tbody>
                        {allDedicated.map((item) => (
                            <tr key={item.id}>
                                <td>
                                    <input
                                        type="text"
                                        value={item.text}
                                        onChange={(e) => handleEditDedicated(item.id, e.target.value)}
                                    />
                                </td>
                                <td>
                                    <button onClick={() => handleDeleteDedicated(item.id)}>🗑 מחק</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                <button onClick={handleAddDedicated}>➕ הוסף הודעה</button>
            </div>


            <Link to="/"><img className="back_button" src={backIcon} alt="Back" /></Link>
        </div>
    );
}

export default Admin;
