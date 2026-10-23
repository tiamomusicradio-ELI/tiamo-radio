import React, {useState} from 'react';
import { Routes, Route, BrowserRouter } from "react-router";

import About from './About.tsx';
import Board from './Board.tsx';
import Home from './Home.tsx';
import Request from './Request.tsx';

import './App.css'; 
import Admin from './admin.tsx';

const RADIO_URL = 'https://liveradio.co.il:8030/stream';

function App() {
  const [control, setControl] = useState(false);

  return (
    <div>
      {control && (
                    <div>
                        <video src={RADIO_URL} style={{ display: 'none' }} autoPlay></video>
                        {/* <iframe src={RADIO_URL} style={{ display: 'none' }} /> */}
                    </div>
                )}

      <div class="bg-image"></div>

      <div className='context'>
      <BrowserRouter basename="/"> 
        <Routes>
          <Route path='about' element={<About />} /> 
          <Route path='board' element={<Board />} /> 
          <Route path='request' element={<Request />} /> 

          <Route path='admin' element={<Admin />} /> 

          <Route path='/' element={<Home setPlay={setControl} isControl={control} />} /> 
          <Route path='*' element={<Home setPlay={setControl} isControl={control} />} /> 
        </Routes>
      </BrowserRouter>
      </div>
    </div>
  );
}

export default App;