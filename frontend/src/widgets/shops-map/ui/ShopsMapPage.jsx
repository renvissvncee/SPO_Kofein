import {useEffect, useRef, useState} from "react";
import './shopsMapPage.scss'
import {api} from '../../../shared/api/baseApi.js'
import {format} from "date-fns"

const ShopsMapPage = ({setCurrentPage,
                          setSelectedShop,
                          selectedHourShops,
                          selectedDate,
                          selectedMinuteShops}) => {
    const mapRef = useRef(null);

    const [activeShop, setActiveShop] = useState(null);

    // ЗАГЛУШКА ТЕЛЕГРАМ ID
    const tg_id = 101;

    // отформатированная дата
    const formatted = format(selectedDate, "yyyy-MM-dd");
    console.log(formatted);

    const [shops, setShops] = useState([]);

    // запрос к апи для получения магазинов (кофеен)
    const loadShops = async (hours, minutes, date) => {
        try {

            let time = null;

            let data = null;

            if (hours && minutes) {
                const pad = (n) => n.toString().padStart(2, '0');
                time = `${pad(hours)}:${pad(minutes)}:00`;


                data = await api.setOrderTime(
                    {
                        "tg_id": tg_id,
                        "date": `${date} ${time}`,
                        "action": "create"
                    });
            }

            else {
                data = await api.getCoffeeShops();
            }

            if (Array.isArray(data)) {
                setShops(data);
            } else {
                setShops([]);
            }

        } catch (err) {
            console.error(err);
            setShops([]);
        }
    }

    // загрузка данных
    useEffect(() => {
        // запрос данных при смене времени: setState внутри loadShops вызывается после ответа API
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadShops(selectedHourShops, selectedMinuteShops, formatted);
    }, [selectedHourShops, selectedMinuteShops]);

    // обработка перехода к странице кофейни
    const handleSelectShop = (shop) => {
        setSelectedShop(shop);
        setCurrentPage('shop');
    };

    // Реализация Яндекс карт через API + доп. кастомизация
    useEffect(() => {
        if (!window.ymaps) return;

        let map;

        window.ymaps.ready(() => {
            // 🗺️ создаём карту
            map = new window.ymaps.Map(mapRef.current, {
                center: [55.7558, 37.6173],
                zoom: 12,
                controls: [
                    "geolocationControl",
                    new window.ymaps.control.ZoomControl({
                        options: {
                            size: "large", // норм кнопки
                            position: {
                                right: 10,
                                top: 100
                            }
                        }
                    })
                ]
            });

            map.options.set({
                minZoom: 3,
                maxZoom: 19,
                suppressMapOpenBlock: true
            });

            map.behaviors.enable([
                "drag",
                "multiTouch",
                "dblClickZoom",
                "scrollZoom"
            ]);

            // 📍 геолокация
            window.ymaps.geolocation.get().then((result) => {
                const userCoords = result.geoObjects.get(0).geometry.getCoordinates();

                map.setCenter(userCoords, 14);

                const userPlacemark = new window.ymaps.Placemark(
                    userCoords,
                    { balloonContent: "Вы здесь" },
                    { preset: "islands#redDotIconWithCaption" }
                );

                map.geoObjects.add(userPlacemark);

                // 🔥 КРИТИЧЕСКИЙ ФИКС ЗУМА
                map.behaviors.disable("multiTouch");
                map.behaviors.enable("multiTouch");
            });



            // ☕ точки
            shops.forEach((shop) => {
                const lat = Number(shop.latitude);
                const lon = Number(shop.longitude);

                if (!lat || !lon) return;

                const placemark = new window.ymaps.Placemark(
                    [lat, lon],
                    {
                        balloonContent: `
                        <div>
                            <strong>${shop.name}</strong><br/>
                            ${shop.address}
                        </div>
                    `,
                        hintContent: shop.name
                    },
                    { preset: "islands#blueIcon" }
                );

                placemark.events.add("click", () => {
                    map.setCenter([lat, lon], 14, { duration: 300 });
                    setActiveShop(shop);
                });

                map.geoObjects.add(placemark);
            });
        });

        return () => {
            if (map) {
                map.destroy();
            }
        };

    }, [shops]);

    return (
        <div className="shops-map-wrapper">
            <div
                ref={mapRef}
                className="shops-map"
            />

            {activeShop && (
                <div className="shop-card">
                    <div className="shop-card__content">
                        <div>
                            <p className="shop-card__title">{activeShop.name}</p>
                            <p className="shop-card__address">{activeShop.address}</p>
                            <p className="shop-card__time">08:00 – 22:00</p>
                        </div>

                        <button
                            className="shop-card__button"
                            onClick={() => handleSelectShop(activeShop)}
                        >
                            Перейти
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};



export default ShopsMapPage;