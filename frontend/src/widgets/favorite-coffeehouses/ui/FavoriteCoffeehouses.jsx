import './favoriteCoffeehouses.scss';
import starhitLogo from '../../../shared/icons/assets/starhit.png';
import surfLogo from '../../../shared/icons/assets/surfLogo.png';
import starsLogo from '../../../shared/icons/assets/starsLogo.png';
import coffeeLikeLogo from '../../../shared/icons/assets/cofelike.jpg';

const FavoriteCoffeehouses = () => {
    const coffeehouses = [
        { id: 1, name: 'Star Hit Cafe', logo: starhitLogo },
        { id: 2, name: 'SURF COFFEE', logo: surfLogo },
        { id: 3, name: 'STARS Coffee', logo: starsLogo },
        { id: 4, name: 'COFFEE LIKE', logo: coffeeLikeLogo },
        { id: 5, name: 'Star Hit Cafe', logo: starhitLogo },
        { id: 6, name: 'SURF COFFEE', logo: surfLogo },
        { id: 7, name: 'STARS Coffee', logo: starsLogo },
        { id: 8, name: 'COFFEE LIKE', logo: coffeeLikeLogo },

    ];

    return (
        <div className="favorite-coffeehouses">
            <h2 className="favorite-coffeehouses__title">
                Любимые кофейни
            </h2>

            <div className="favorite-coffeehouses__list">
                {coffeehouses.map(coffeehouse => (
                    <div key={coffeehouse.id}
                         className="favorite-coffeehouses__item">

                        {coffeehouse.logo && (
                            <div className="favorite-coffeehouses__logo">
                                <img style={{
                                    width: '100%',
                                    height: '100%',
                                    objectFit: 'cover'
                                }}  src={coffeehouse.logo} alt={coffeehouse.name} />
                            </div>
                        )}

                        <span className="favorite-coffeehouses__name">
                            {coffeehouse.name}
                        </span>

                    </div>
                ))}
            </div>
        </div>
    );
};

export default FavoriteCoffeehouses;