import './bottomNavigation.scss'
import { useState, useRef, useEffect } from 'react';
import '../../../shared/lib/react-bits/glass-surface/glassSurface.css';
import GlassSurface from "../../../shared/lib/react-bits/glass-surface/GlassSurface.jsx";
import {Clock, Coffee} from 'lucide-react';

const BottomNavigation = ({setCurrentPage, currentPage, }) => {
    const activeIndex = currentPage === 'home' ? 0 : 1;
    const [offset, setOffset] = useState(0);

    const buttonsRef = useRef([]);
    const navRef = useRef(null);

    useEffect(() => {
        const btn = buttonsRef.current[activeIndex];
        const nav = navRef.current;

        if (btn && nav) {
            const btnRect = btn.getBoundingClientRect();
            const navRect = nav.getBoundingClientRect();

            const center =
                btnRect.left -
                navRect.left +
                btnRect.width / 2;

            setOffset(center);
        }
    }, [activeIndex]);

    return (
        <GlassSurface
            width="auto"
            height="auto"
            borderRadius={50}
            /* стекло */
            backgroundOpacity={0.45}   // ← БОЛЬШЕ БЕЛОГО
            opacity={0.9}             // почти непрозрачный
            brightness={50}           // светлее

            /* эффект стекла */
            displace={2}             // меньше шума (у тебя было 2 — это жестко)
            distortionScale={-40}      // мягче

            /* цветные смещения */
            redOffset={0}
            greenOffset={6}
            blueOffset={10}

            saturation={0.5}           // чуть насыщеннее фон

            mixBlendMode="normal"
            borderWidth={0.2}
            style={{
                position: 'fixed',
                bottom: '25px',
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: 1000,
                paddingLeft: '5px',
                paddingRight: '5px'
            }}
        >
            <nav className="bottomNav" ref={navRef}>

                {/* 🔥 Индикатор */}
                <GlassSurface
                    width={70}
                    height={60}
                    borderRadius={40}
                    /* делаем его ярче, чем фон */
                    backgroundOpacity={0.5}
                    opacity={1}
                    brightness={135}

                    /* почти без искажений */
                    displace={0.15}
                    distortionScale={-25}

                    saturation={0.5}

                    redOffset={0}
                    greenOffset={2}
                    blueOffset={4}

                    mixBlendMode="normal"
                    style={{
                        position: 'absolute',
                        top: '50%',
                        transform: `translate(${offset - 35}px, -50%)`,
                        transition: 'transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)',
                        pointerEvents: 'none',
                        zIndex: 1,
                    }}
                />

                {[0, 1].map((i) => (
                    <button
                        key={i}
                        ref={(el) => (buttonsRef.current[i] = el)}
                        className={`bottomNav__item ${activeIndex === i ? 'active' : ''}`}
                        onClick={() => {

                            (i === 0 ? setCurrentPage('home') : setCurrentPage('shops'));

                        }}
                        style={{ position: 'relative', zIndex: 2 }}
                    >
                        {i === 0 ? <Clock/>: <Coffee/>}
                    </button>
                ))}

            </nav>
        </GlassSurface>
    )
}

export default BottomNavigation;