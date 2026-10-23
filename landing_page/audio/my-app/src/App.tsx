import { useState, useRef, type JSX } from "react";

interface Track {
  id: number;
  title: string;
  src: string;
}

const tracks: Track[] = Array.from({ length: 30 }).map((_, i) => ({
  id: i,
  title: `קטע ${i + 1}`,
  src: `/audio/track${i + 1}.mp3`, // קבצים מקומיים בתיקיית public/audio
}));

export default function App(): JSX.Element {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [current, setCurrent] = useState<Track | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [showCopyright, setShowCopyright] = useState<boolean>(false);

  const playTrack = (track: Track): void => {
    if (!audioRef.current) return;

    if (current?.id !== track.id) {
      audioRef.current.src = track.src;
    }

    audioRef.current.play();
    setCurrent(track);
    setIsPlaying(true);
    setShowCopyright(true);
  };

  const togglePlay = (): void => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }

    setIsPlaying(!isPlaying);
  };

  const handleTimeUpdate = (): void => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;

    setProgress((audio.currentTime / audio.duration) * 100);
  };

  return (
    <div
      className="min-h-screen bg-cover bg-center flex flex-col"
      style={{ backgroundImage: "url('/background.jpeg')" }}
    >
      <div className="bg-white/70 flex-1 p-6">
        <h1 className="text-3xl font-bold text-black text-center mb-6">
          רוחות המדבר – חלק א
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl mx-auto">
          {tracks.map((track) => (
            <button
              key={track.id}
              onClick={() => playTrack(track)}
              className={`p-3 rounded-xl text-right shadow transition ${
                current?.id === track.id
                  ? "bg-black text-white"
                  : "bg-white hover:bg-gray-100"
              }`}
            >
              {track.title}
            </button>
          ))}
        </div>
      </div>

      {/* נגן תחתון */}
      <div className="bg-black text-white p-4">
        <audio
          ref={audioRef}
          onTimeUpdate={handleTimeUpdate}
          onEnded={() => setIsPlaying(false)}
        />

        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-4">
            <button
              onClick={togglePlay}
              className="px-4 py-2 rounded-xl bg-white text-black"
            >
              {isPlaying ? "הפסק" : "נגן"}
            </button>

            <div className="flex-1 h-2 bg-gray-600 rounded">
              <div
                className="h-2 bg-white rounded"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {showCopyright && (
            <div className="text-sm text-center mt-2">
              זכויות יוצרים של...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
