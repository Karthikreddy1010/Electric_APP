import { motion } from 'framer-motion';

export default function Background3D() {
  // Y coordinates for exponential horizontal perspective lines
  const horizLines = [210, 222, 238, 258, 285, 320, 368, 432, 520, 642, 810, 1000];

  // X coordinates at the bottom of vertical perspective lines
  const vertLines = [
    -1000, -600, -300, -100, 50, 150, 250, 320, 380, 430, 470, 500, 530, 570, 620, 680, 750, 850, 950, 1100, 1300, 1600, 2000
  ];

  return (
    <div className="absolute inset-0 w-full h-full bg-[#070a13] overflow-hidden pointer-events-none select-none">
      {/* Dark background radial gradients for atmospheric depth */}
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-[800px] h-[500px] rounded-full bg-cyan-900/10 blur-[140px]" />
      <div className="absolute bottom-0 left-0 right-0 h-[40%] bg-gradient-to-t from-[#04060b] to-transparent" />

      {/* SVG 3D Perspective Grid */}
      <svg
        className="absolute inset-0 w-full h-full opacity-35"
        viewBox="0 0 1000 1000"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="grid-fade" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#00f2ff" stopOpacity="0.0" />
            <stop offset="25%" stopColor="#00f2ff" stopOpacity="0.25" />
            <stop offset="70%" stopColor="#00f2ff" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#00f2ff" stopOpacity="0.7" />
          </linearGradient>
        </defs>

        {/* Radiating perspective lines */}
        {vertLines.map((xVal, idx) => (
          <line
            key={`v-${idx}`}
            x1="500"
            y1="200"
            x2={xVal.toString()}
            y2="1000"
            stroke="url(#grid-fade)"
            strokeWidth={xVal === 500 ? "1.5" : "1"}
          />
        ))}

        {/* Transverse perspective lines */}
        {horizLines.map((yVal, idx) => {
          // Fade opacity based on distance from horizon
          const opacity = (idx / horizLines.length) * 0.7;
          return (
            <line
              key={`h-${idx}`}
              x1="-1000"
              y1={yVal.toString()}
              x2="2000"
              y2={yVal.toString()}
              stroke="#00f2ff"
              strokeOpacity={opacity}
              strokeWidth="1"
            />
          );
        })}
      </svg>

      {/* Glowing cybernetic orb at the vanishing point */}
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center justify-center">
        {/* Core glow */}
        <div className="absolute w-24 h-24 rounded-full bg-cyan-500/20 blur-xl animate-pulse" />
        <div className="absolute w-12 h-12 rounded-full bg-[#00f2ff]/30 blur-md" />
        
        {/* Outer rotating vector rings (Cyber-Orb) */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 15, ease: 'linear' }}
          className="absolute w-32 h-32 rounded-full border border-dashed border-[#00f2ff]/40"
        />
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ repeat: Infinity, duration: 25, ease: 'linear' }}
          className="absolute w-44 h-44 rounded-full border border-dashed border-blue-500/30"
        />
        
        {/* Orb Constellation Nodes */}
        <svg className="absolute w-40 h-40" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="8" fill="#00f2ff" className="shadow-[0_0_10px_#00f2ff] animate-pulse" />
          <circle cx="50" cy="50" r="1" fill="#fff" />

          {/* Connected points */}
          <line x1="50" y1="50" x2="30" y2="30" stroke="#00f2ff" strokeWidth="0.5" strokeOpacity="0.6" />
          <line x1="50" y1="50" x2="70" y2="30" stroke="#00f2ff" strokeWidth="0.5" strokeOpacity="0.6" />
          <line x1="50" y1="50" x2="50" y2="15" stroke="#3b82f6" strokeWidth="0.5" strokeOpacity="0.6" />
          <line x1="50" y1="50" x2="25" y2="60" stroke="#3b82f6" strokeWidth="0.5" strokeOpacity="0.6" />
          <line x1="50" y1="50" x2="75" y2="60" stroke="#00f2ff" strokeWidth="0.5" strokeOpacity="0.6" />

          <circle cx="30" cy="30" r="2" fill="#00f2ff" />
          <circle cx="70" cy="30" r="2.5" fill="#3b82f6" className="animate-ping" />
          <circle cx="50" cy="15" r="2" fill="#00f2ff" />
          <circle cx="25" cy="60" r="3" fill="#00f2ff" className="animate-pulse" />
          <circle cx="75" cy="60" r="2" fill="#3b82f6" />
        </svg>
      </div>
    </div>
  );
}
