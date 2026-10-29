import React, {useState, useRef, useEffect, useMemo} from 'react'
import './timePicker.scss'

const hours = Array.from({ length: 24 }, (_, i) =>
    i.toString().padStart(2, '0')
)

const minutes = Array.from({ length: 60 }, (_, i) =>
    i.toString().padStart(2, '0')
)

const digitSize = 90

const LOOP_MULTIPLIER_HOURS = 20
const LOOP_MULTIPLIER_MINUTES = 12

const TimePicker = ({setSelectedHourUp, setSelectedMinuteUp}) => {

    const [selectedHour, setSelectedHour] = useState(() => {
        const now = new Date()
        return now.getHours().toString().padStart(2, '0')
    })

    const [selectedMinute, setSelectedMinute] = useState(() => {
        const now = new Date()
        return now.getMinutes().toString().padStart(2, '0')
    })

    const hoursRef = useRef(null)
    const minutesRef = useRef(null)

    const triggerHaptic = () => {
        if (navigator.vibrate) {
            navigator.vibrate(5); // короткий "тик"
        }
    };

    // 🔁 виртуальные массивы
    const virtualHours = useMemo(() =>
            Array.from(
                { length: hours.length * LOOP_MULTIPLIER_HOURS },
                (_, i) => hours[i % hours.length]
            ),
        [])

    const virtualMinutes = useMemo(() =>
            Array.from(
                { length: minutes.length * LOOP_MULTIPLIER_MINUTES },
                (_, i) => minutes[i % minutes.length]
            ),
        [])

    // ✅ конфиг (оптимизация)
    const getConfig = (baseList) => {
        const multiplier =
            baseList === hours
                ? LOOP_MULTIPLIER_HOURS
                : LOOP_MULTIPLIER_MINUTES

        const totalLength = baseList.length * multiplier

        return {
            totalLength,
            middle: Math.floor(totalLength / 2),
            safeZoneStart: baseList.length * 2,
            safeZoneEnd: totalLength - baseList.length * 2,
        }
    }

    // ✅ initial scroll
    useEffect(() => {
        const init = (ref, list, value) => {
            const container = ref.current
            if (!container) return

            const baseIndex = list.findIndex(v => v === value)

            const { middle } = getConfig(list)

            const index = middle + baseIndex

            container.scrollTop = index * digitSize
        }

        requestAnimationFrame(() => {
            init(hoursRef, hours, selectedHour)
            init(minutesRef, minutes, selectedMinute)
        })
    }, [])

    const handleScroll = (ref, baseList, setter, setterUp) => {

        const container = ref.current
        if (!container) return

        const scrollTop = container.scrollTop
        const index = Math.round(scrollTop / digitSize)

        const valueIndex =
            ((index % baseList.length) + baseList.length) %
            baseList.length
        const nextValue = baseList[valueIndex];

        setter(prev => {
            if (prev !== nextValue) {
                // обновляем локально
                triggerHaptic();


                const updated = nextValue;

                // 🔹 дебаунс для родителя
                if (setterUp) {
                    if (setterUp.debounceTimeout) clearTimeout(setterUp.debounceTimeout);
                    setterUp.debounceTimeout = setTimeout(() => {
                        setterUp(updated);
                    }, 10); // 50 мс задержка
                }

                return updated;
            }
            return prev;
        });

        const { middle, safeZoneStart, safeZoneEnd } =
            getConfig(baseList)

        if (index < safeZoneStart || index > safeZoneEnd) {
            const newIndex = middle + valueIndex
            container.scrollTop = newIndex * digitSize
        }
    }

    return (
        <div className="timePicker">
            <div className="timePicker__full_box">
                <div className="timePicker__box">
                    <div
                        ref={hoursRef}
                        className="timePicker__column"
                        onScroll={() =>
                            handleScroll(hoursRef, hours, setSelectedHour, setSelectedHourUp)
                        }
                    >
                        {virtualHours.map((hour, i) => (
                            <div
                                key={i}
                                className={`timePicker__item ${
                                    selectedHour === hour ? 'active' : ''
                                }`}
                            >
                                {hour}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="timePicker__separator">:</div>

            <div className="timePicker__full_box">
                <div className="timePicker__box">
                    <div
                        ref={minutesRef}
                        className="timePicker__column"
                        onScroll={() =>
                            handleScroll(minutesRef, minutes, setSelectedMinute, setSelectedMinuteUp)
                        }
                    >
                        {virtualMinutes.map((minute, i) => (
                            <div
                                key={i}
                                className={`timePicker__item ${
                                    selectedMinute === minute ? 'active' : ''
                                }`}
                            >
                                {minute}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default React.memo(TimePicker);