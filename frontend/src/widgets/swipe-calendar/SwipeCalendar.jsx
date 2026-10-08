import { useState, useRef } from "react";
import {
    format,
    addMonths,
    subMonths,
    startOfMonth,
    endOfMonth,
    eachDayOfInterval,
    isSameDay,
    isBefore
} from "date-fns";
import { useSwipeable } from "react-swipeable";
import "./swipeCalendar.scss";

import { ChevronLeft, ChevronRight } from "lucide-react";

const SwipeCalendar = ({ selectedDate, setSelectedDate, onClose }) => {

    const today = new Date();

    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [direction, setDirection] = useState(null);
    const calendarRef = useRef(null);



    const weekDays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

    const changeMonth = (dir) => {
        let newMonth = currentMonth;
        if (dir === "left") {
            newMonth = addMonths(currentMonth, 1);
        } else {
            const prevMonth = subMonths(currentMonth, 1);
            const now = new Date();
            if (
                prevMonth.getFullYear() < now.getFullYear() ||
                (prevMonth.getFullYear() === now.getFullYear() &&
                    prevMonth.getMonth() < now.getMonth())
            ) {
                // не листаем на прошлые месяцы

                return;
            } else {
                newMonth = prevMonth;
            }
        }

        if (newMonth.getTime() === currentMonth.getTime()) return; // если месяц не поменялся — не делаем анимацию

        setDirection(dir);
        setCurrentMonth(newMonth);
    };

    const handlers = useSwipeable({
        onSwipedLeft: () => changeMonth("left"),
        onSwipedRight: () => changeMonth("right"),
        trackMouse: true
    });

    // закрытие по клику вне календаря
    const handleOverlayClick = (e) => {
        if (!calendarRef.current.contains(e.target)) {
            onClose();
        }
    };

    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const days = eachDayOfInterval({ start: monthStart, end: monthEnd });

    // пустые клетки перед первым днём месяца (понедельник = 0)
    const startWeekDay = (monthStart.getDay() + 6) % 7;
    const blanks = Array.from({ length: startWeekDay });

    return (
        <div className="swipe-calendar-overlay" onClick={handleOverlayClick}>
            <div className="swipe-calendar" ref={calendarRef}>
                <div className="calendar-header">
                    <button
                        className="month-btn"
                        onClick={() => changeMonth("right")}
                        aria-label="Previous month"
                    >
                        <ChevronLeft />
                    </button>

                    <span>{format(currentMonth, "LLLL yyyy")}</span>

                    <button
                        className="month-btn"
                        onClick={() => changeMonth("left")}
                        aria-label="Next month"
                    >
                        <ChevronRight />
                    </button>
                </div>

                <div className="calendar-weekdays">
                    {weekDays.map((day) => (
                        <div key={day} className="calendar-weekday">
                            {day}
                        </div>
                    ))}
                </div>

                <div
                    className={`calendar-days slide-${direction}`}
                    key={currentMonth}
                    {...handlers}
                >
                    {blanks.map((_, i) => (
                        <div key={"blank" + i} className="calendar-day blank"></div>
                    ))}

                    {days.map((day) => (
                        <button
                            key={day.toISOString()}
                            disabled={isBefore(day, new Date().setHours(0, 0, 0, 0))}
                            className={`calendar-day ${
                                isSameDay(day, selectedDate || today) ? "selected" : ""
                            }`}
                            onClick={() => {
                                setSelectedDate(day);
                            }}
                        >
                            {format(day, "d")}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default SwipeCalendar;