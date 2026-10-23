import React from 'react';
import { Link } from 'react-router-dom';

import './about.css'

import backIcon from './back.png';

function About() {
    const BackButton = () => {
        return <Link to="/"><img className="back_button" src={backIcon}/></Link>
    }

    const Description = () => {
        return <div className="description">
            <span className="script">
            <u>רדיו TIAMO MUSIC </u> <br />
נועד לשדר למאזינים מוסיקה באוירה אחרת . <br />
"מוסיקה לנשמה" המיועדת לכל אלה שהמוסיקה מהווה עבורם נוסטלגיה, והערכה למלודיה מכל הסגנונות אך בדגש על מוסיקה אתנית מכל התפוצות , מוסיקה הפורצת את כל הגבולות מהמזרח, הדרום, הצפון והמערב.  <br />
בתחנה תאזינו למוסיקה מכל גווני הקשת , וכמו תמיד תיהיה מרוממת ומענגת , ותחבר בין אנשים תקופות ואהבה למוסיקה טובה. <br />
כל זאת, לצד תוכניות קצרות של פודקסטים בתחומי הייעוץ לחיים לטובת קהל מאזיני התחנה <br />
האזנה נעימה לכולם.
                </span>
        </div>
    }

    return (
        <div className="about_container">
            <Description />

            <BackButton />
        </div>
    );
}

export default About;