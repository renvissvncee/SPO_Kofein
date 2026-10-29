const ScrollableContainer = ({ children }) => {
    return (
        <div style={{ overflowY: 'auto', height: '100vh' }}>
            {children}
        </div>
    );
};

export default ScrollableContainer;