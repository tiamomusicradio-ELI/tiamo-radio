import React, { useState } from 'react';
import { Link } from 'react-router-dom';

import './about.css';
import backIcon from './back.png';

function Request() {
    const [name, setName] = useState("");
    const [songName, setSongName] = useState("");
    const [artist, setArtist] = useState("");
    const [dedication, setDedication] = useState("");

    const BackButton = () => {
        return <Link to="/"><img className="back_button" src={backIcon} alt="Back" /></Link>;
    };

    const handelSubmit = () => {
        if (!name || !songName || !artist) {
            alert("אנא מלא את כל השדות");
            return;
        }

        let message = `שלום,\nאני ${name} ומבקש את השיר:\nשם השיר:  *${songName}*\nשם הזמר: *${artist}*\n הקדשה מיוחדת: ${dedication}`;

        let phoneNumber = "972538550511"; 
        let whatsappLink = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(message)}`;
        window.open(whatsappLink, "_blank");
    };

    return (
        <div className="about_container">
            <div className="container">
                <div className="subtitle">בא לי לשמוע</div>

                <label>שם מלא</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} /><br/>

                <label>שם השיר המבוקש</label>
                <input type="text" value={songName} onChange={(e) => setSongName(e.target.value)} /><br />

                <label>שם הזמר</label>
                <input type="text" value={artist} onChange={(e) => setArtist(e.target.value)} /><br />

                <label>בקשה מיוחדת</label>
                <input type="text" value={dedication} onChange={(e) => setDedication(e.target.value)} /><br />

                <div className="button" onClick={handelSubmit}>שליחה</div>
            </div>

            <BackButton />
        </div>
    );
}

export default Request;
