import '../shops/shopsPage.scss'
import {useState} from "react";
import ShopsListPage from "../../widgets/shops-list/ui/ShopsListPage.jsx";

import ShopsMapPage from "../../widgets/shops-map/ui/ShopsMapPage.jsx";
import FavoriteCoffeehouses from "../../widgets/favorite-coffeehouses/ui/FavoriteCoffeehouses.jsx";
import PromoSlider from "../../widgets/promo-slider/ui/PromoSlider.jsx";

const ShopsPage = ({ setCurrentPage, setSelectedShop,
                   selectedHourShops, selectedMinuteShops,
                       selectedDate={selectedDate},
                       setSelectedDate={setSelectedDate}}) => {

    const [currentShopsPage, setCurrentShopsPage] = useState('list');

    const renderPage = () => {

        switch (currentShopsPage) {
            case 'list':
                return <ShopsListPage setCurrentPage={setCurrentPage}
                                      setSelectedShop={setSelectedShop}
                                      selectedHourShops={selectedHourShops}
                                      selectedMinuteShops={selectedMinuteShops}
                                      selectedDate={selectedDate}/>;
            default:
                return <ShopsMapPage setCurrentPage={setCurrentPage}
                                      setSelectedShop={setSelectedShop}
                                      selectedHourShops={selectedHourShops}
                                      selectedMinuteShops={selectedMinuteShops}
                                     selectedDate={selectedDate}/>;
        }
    };
    return (
        <div className={`shops-page ${currentShopsPage === 'map' ? 'map-mode' : ''}`}>
            <div className="shops-tabs-wrapper"> {/* 👈 добавили обертку */}
                <div className="shops-tabs">
                    <button className="shops-tabs__button" onClick={() => setCurrentShopsPage('list')}>
                        кофейни
                    </button>

                    <button className="shops-tabs__button" onClick={() => setCurrentShopsPage('map')}>
                        карта
                    </button>
                </div>
            </div>

            <div className="shops-content">
                {currentShopsPage === 'list' && (

                    <div style={{ marginTop: '1px'}}>

                        <PromoSlider />

                        <FavoriteCoffeehouses />
                        <h2 className="favorite-coffeehouses__closest">
                            Поблизости
                        </h2>
                    </div>
                )}
                {renderPage()}
            </div>
        </div>
    )
}

export default ShopsPage;