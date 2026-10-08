import '../ui/shopsListPage.scss'
import {useEffect, useState} from "react";
import {api} from "../../../shared/api/baseApi.js";
import {format} from "date-fns"
import ProductCover from "../../../shared/icons/assets/product_cover.png"
import FavoriteCoffeehouses from "../../favorite-coffeehouses/ui/FavoriteCoffeehouses.jsx";

const ShopsListPage = ({ setCurrentPage,
                           setSelectedShop,
                       selectedHourShops, selectedMinuteShops,
                       selectedDate}) => {


    // заглушка для кофеен
    /*const mockShops = [
        {
            id: 1,
            name: "M Coffee",
            address: "9 Парковая, 34",
            coffee_shop_image: ProductCover,
        },
        {
            id: 2,
            name: "Coffee Like",
            address: "Невский проспект, 12",
            coffee_shop_image: ProductCover,
        },
        {
            id: 3,
            name: "Surf Coffee",
            address: "ул. Ленина, 45",
            coffee_shop_image: ProductCover,
        }
    ];*/


    // ЗАГЛУШКА ТЕЛЕГРАМ ID
    const tg_id = 0;

    // отформатированная дата
    const formatted = format(selectedDate, "yyyy-MM-dd");
    console.log(formatted);

    const [shops, setShops] = useState([]);
    const [loading, setLoading] = useState(false);


    // запрос к апи для получения магазинов (кофеен)
    const loadShops = async (hours, minutes, date) => {
        try {
            setLoading(true);

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
        } finally {
            setLoading(false);
        }
    }

    // заглушка для mock данных о кофейне
    /*const loadShops = async () => {
        setLoading(true);
    };*/


    useEffect(() => {
        loadShops(selectedHourShops, selectedMinuteShops, formatted);
    }, [selectedHourShops, selectedMinuteShops]);


    const handleSelectShop = (shop) => {
        setSelectedShop(shop);
        setCurrentPage('shop');
    };

    return (
        <div className="shops-list">

            {loading ? (
                <p className="shops-list__empty">Загрузка...</p>
            ) : shops.length === 0 ? (
                <p className="shops-list__empty">
                    Нет доступных кофеен
                </p>
            ) : (

                shops.map(shop => (
                    <div
                        key={shop.id}
                        className="shops-list__item"
                        onClick={() => handleSelectShop(shop)}
                    >
                        <div className="shops-list__image-wrapper">
                            <img
                                src={shop.coffee_shop_image}
                                alt=""
                                className="shops-list__image"
                            />
                        </div>
                        <div className="shops-list__info">
                            <p className="shops-list__title">{shop.name}</p>
                            <p className="shops-list__address">{shop.address}</p>
                        </div>
                    </div>
                ))
            )


            }
        </div>
    )
}

export default ShopsListPage