import {useState, useEffect} from 'react';
import './timeCard.scss';
import '../../../widgets/time-picker/ui/TimePicker.jsx'
import TimePicker from "../../time-picker/ui/TimePicker.jsx";
import {Clock, Calendar} from "lucide-react";
import SwipeCalendar from "../../swipe-calendar/SwipeCalendar.jsx"

const TimeCard = ({setCurrentPage,
                      setSelectedHourShops,
                      setSelectedMinuteShops,
                      selectedDate, setSelectedDate}) => {

    // работа с календарем
    const [isCalendarOpen, setIsCalendarOpen] = useState(false);


    useEffect(() => {
        setSelectedHourShops(null);
        setSelectedMinuteShops(null);
    }, []);




    const [selectedHour, setSelectedHour] = useState(
        new Date().getHours().toString().padStart(2, '0')
    )
    const [selectedMinute, setSelectedMinute] = useState(
        new Date().getMinutes().toString().padStart(2, '0')
    )

    // Нажатие кнопки выбора даты (Календарь)
    const handleCalendarClick = () => {
        setIsCalendarOpen(prev => !prev);
    }



    // Нажатие кнопки "Найти кофейню"
    const handleTimeClick = () => {
        setSelectedHourShops(selectedHour);
        setSelectedMinuteShops(selectedMinute);
        setCurrentPage('shops');
    }



    return (
        <div className="time-card">

            <div className="time-card__header">
                <Clock className="time-card__header__choose-time" />
                <p className="time-card__header__choose-time">Выберите время</p>
            </div>

            <TimePicker
                selectedHourUp={selectedHour}
                selectedMinuteUp={selectedMinute}
                setSelectedHourUp={setSelectedHour}
                setSelectedMinuteUp={setSelectedMinute}
            />


            <div className="time-card__search-date-wrapper">
                <button className="time-card__search-button" onClick={handleTimeClick}>
                    Найти кофейню
                </button>

                <div className="date-wrapper">
                    <button className="time-card__date-button" onClick={handleCalendarClick}>
                        <Calendar className="time-card__choose-date" />
                    </button>

                    {isCalendarOpen && (
                        <SwipeCalendar
                            selectedDate={selectedDate}
                            setSelectedDate={setSelectedDate}

                            onClose={() => setIsCalendarOpen(false)}
                        />
                    )}

                </div>
            </div>
        </div>
    );
};

export default TimeCard;