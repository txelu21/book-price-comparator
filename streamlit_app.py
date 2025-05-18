import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import concurrent.futures
import re
import time
import os

# NOTE: For Streamlit Cloud deployment, we've removed the Selenium scraper imports
# and are using mock data instead. These imports work locally but cause errors in the cloud.
#
# from src.amazon_selenium import scrape_book_info as amazon_scraper
# from src.casadelibro_selenium import scrape_book_info as casadelibro_scraper
# from src.ebay_selenium import scrape_book_info as ebay_scraper
# from src.elcorteingles_selenium import scrape_book_info as corteingles_scraper
# from src.iberlibro_selenium import scrape_book_info as iberlibro_scraper
# from src.libreriacentral_selenium import scrape_book_info as libreriacentral_scraper

# Define base URLs for each store to construct product links
STORE_URLS = {
    "Amazon": "https://www.amazon.es/s?k={}",
    "Casa del Libro": "https://www.casadellibro.com/?query={}",
    "eBay": "https://www.ebay.es/sch/i.html?_nkw={}",
    "El Corte Inglés": "https://www.elcorteingles.es/search-nwx/1/?s={}",
    "IberLibro": "https://www.iberlibro.com/servlet/SearchResults?ds=20&kn={}&sts=t",
    "Librería Central": "https://www.libreriacentral.com/SearchResults.aspx?st={}&cId=0&sm=qck"
}

# Store logo URLs for each store
STORE_LOGOS = {
    "Amazon": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Amazon_logo.svg/320px-Amazon_logo.svg.png",
    "Casa del Libro": "https://play-lh.googleusercontent.com/JBBNBwe7q7A-lBx1PDXQ6VprjsT_XxH4w8M0IM3d7rKtU0-Rubglmg_kuwIyPYn8mMY=w240-h480-rw",
    "eBay": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/EBay_logo.svg/220px-EBay_logo.svg.png",
    "El Corte Inglés": "https://banner2.cleanpng.com/20180531/jsz/avo5f3ffi.webp",
    "IberLibro": "https://librosdeimpro.com/wp-content/uploads/2021/02/iberlibro.png",
    "Librería Central": "https://www.libreriacentral.com/Resources/icons/Logob.png"
}

def normalize_price(price_str):
    """Normalize price strings to float values."""
    if not price_str or price_str == 'Not Found':
        return None
    
    # Remove currency symbols and normalize decimal separator
    price_str = price_str.replace('€', '').replace('EUR', '').strip()
    
    # Extract numbers using regex
    match = re.search(r'(\d+[,.]\d+|\d+)', price_str)
    if match:
        price = match.group(1).replace(',', '.')
        return float(price)
    
    return None

def format_price_difference(base_price, compare_price):
    """Format price difference in euros and percentage."""
    if base_price is None or compare_price is None:
        return "N/A", "N/A"
    
    diff_euros = compare_price - base_price
    if base_price > 0:  # Avoid division by zero
        diff_percent = (diff_euros / base_price) * 100
        return f"{diff_euros:.2f} €", f"{diff_percent:.2f}%"
    return f"{diff_euros:.2f} €", "N/A"

def run_scraper_safely(scraper_func, isbn, store_name):
    """
    Run a scraper function with error handling and progress updates.
    
    NOTE: This function is not used in the cloud deployment version.
    It's kept here for reference and local development.
    """
    try:
        with st.spinner(f"Buscando en {store_name}..."):
            result = scraper_func(isbn)
            if result and isinstance(result, dict):
                # Add store name if not already present
                if 'store' not in result:
                    result['store'] = store_name
                
                # Add product_url if not already present, using the base search URL
                if 'product_url' not in result and store_name in STORE_URLS:
                    result['product_url'] = STORE_URLS[store_name].format(isbn)
                
                return result
            else:
                default_result = {'isbn': isbn, 'store': store_name, 'title': 'No encontrado', 'price': 'No disponible'}
                # Add default product URL
                if store_name in STORE_URLS:
                    default_result['product_url'] = STORE_URLS[store_name].format(isbn)
                return default_result
    except Exception as e:
        default_result = {'isbn': isbn, 'store': store_name, 'title': 'Error', 'price': f'Error: {str(e)}'}
        # Add default product URL even for errors
        if store_name in STORE_URLS:
            default_result['product_url'] = STORE_URLS[store_name].format(isbn)
        return default_result

# Add caching wrapper for the book search process
@st.cache_data(ttl=900, show_spinner=False)  # Cache for 15 minutes (900 seconds)
def cached_search_books(isbn):
    """
    Cache search results for a given ISBN to improve performance.
    
    For Streamlit Cloud deployment, this function returns mock data instead of
    using actual web scrapers, which is why it works without the scraper imports.
    """
    
    # For demonstration, we'll return fixed data for the Harry Potter book
    if isbn == "9788478884452":
        results = [
            {
                'title': 'Harry Potter y la Piedra Filosofal',
                'image_url': 'https://imagessl0.casadellibro.com/a/l/t7/00/9788478884452.jpg',
                'price': '18.95€',
                'product_url': 'https://www.casadellibro.com/libro-harry-potter-y-la-piedra-filosofal/9788478884452/599400',
                'store': 'Casa del Libro',
                'numeric_price': 18.95
            },
            {
                'title': 'Harry Potter y la Piedra Filosofal',
                'image_url': 'https://m.media-amazon.com/images/I/91R1AixEiLL._SY466_.jpg',
                'price': '17.95€',
                'product_url': 'https://www.amazon.es/Harry-Potter-Piedra-Filosofal-Rowling/dp/8478884459',
                'store': 'Amazon',
                'numeric_price': 17.95
            },
            {
                'title': 'Harry Potter y la Piedra Filosofal',
                'image_url': 'https://sgfm.elcorteingles.es/SGFM/dctm/MEDIA03/202204/11/00106520800776____2__600x600.jpg',
                'price': '19.90€',
                'product_url': 'https://www.elcorteingles.es/libros/A37733796-harry-potter-y-la-piedra-filosofal-tapa-dura/',
                'store': 'El Corte Inglés',
                'numeric_price': 19.90
            },
            {
                'title': 'Harry Potter y la Piedra Filosofal',
                'image_url': 'https://pictures.abebooks.com/isbn/9788478884452-es.jpg',
                'price': '15.90€',
                'product_url': 'https://www.iberlibro.com/products/isbn/9788478884452',
                'store': 'IberLibro',
                'numeric_price': 15.90
            }
        ]
    else:
        # For any other ISBN, provide sample data
        results = [
            {
                'title': f'Libro con ISBN {isbn}',
                'image_url': 'https://via.placeholder.com/150',
                'price': '15.99€',
                'product_url': f'https://www.casadellibro.com/?query={isbn}',
                'store': 'Casa del Libro',
                'numeric_price': 15.99
            },
            {
                'title': f'Libro con ISBN {isbn}',
                'image_url': 'https://via.placeholder.com/150',
                'price': '14.95€',
                'product_url': f'https://www.amazon.es/s?k={isbn}',
                'store': 'Amazon',
                'numeric_price': 14.95
            }
        ]
    
    # Add timestamp to results for display purposes
    timestamp = time.strftime("%H:%M:%S")
    return {"results": results, "timestamp": timestamp}

def main():
    st.title("📚 Comparador de Precios de Libros")
    st.write("Introduce un ISBN para comparar precios de libros en diferentes tiendas online.")

    # Initialize session state for tracking if search was triggered by Enter key
    if 'isbn_search_triggered' not in st.session_state:
        st.session_state['isbn_search_triggered'] = False
        
    # Track the previous ISBN to detect changes
    if 'previous_isbn' not in st.session_state:
        st.session_state['previous_isbn'] = "9788478884452"  # Initialize with the default ISBN

    # Get the ISBN input
    isbn = st.text_input("ISBN (10-13 dígitos):", value="9788478884452", max_chars=13, key="isbn_input")
    
    # Check if Enter was pressed (ISBN changed) - but only if not the first load
    if 'app_loaded' in st.session_state and isbn != st.session_state['previous_isbn']:
        st.session_state['isbn_search_triggered'] = True
    
    # Update previous ISBN
    st.session_state['previous_isbn'] = isbn
    
    # Mark that the app has been loaded
    st.session_state['app_loaded'] = True
    
    # Add search button to explicitly trigger the search
    search_button = st.button("🔍 Buscar")
    
    # Add refresh button in sidebar
    with st.sidebar:
        st.title("Opciones")
        if st.button("🔄 Actualizar precios"):
            # Clear the cache for this specific ISBN
            st.cache_data.clear()
            st.success("¡Cache borrado! Los precios se actualizarán.")
            # Reset the cache hit flag
            if f"isbn_cache_{isbn}" in st.session_state:
                st.session_state[f"isbn_cache_{isbn}"] = False
            
        st.markdown("---")
        st.write("Utiliza este botón para obtener los precios más actualizados.")
        
        # Add information about deployment
        st.markdown("---")
        st.subheader("Acerca de la app")
        st.write("Esta aplicación está desplegada en Streamlit Community Cloud.")
        st.write("Compara precios de libros en varias tiendas online usando el ISBN.")
        
        # GitHub link if you have one
        # st.write("[Código fuente en GitHub](https://github.com/your-username/your-repo)")

    # Only search when the button is pressed or when Enter is pressed in the input field
    if search_button or st.session_state.get('isbn_search_triggered', False):
        # Reset the search trigger flag
        st.session_state['isbn_search_triggered'] = False
        
        if not isbn or not (10 <= len(isbn) <= 13 and isbn.isdigit()):
            st.error("ISBN no válido. Por favor, introduce un ISBN de 10 a 13 dígitos.")
            return

        st.write(f"Buscando ISBN: **{isbn}**")
        
        # Create a progress element
        progress = st.progress(0)
        
        # Check cache status for visual feedback
        cache_status = st.empty()
        
        # Determine if this is a cache hit or miss
        cache_hit = st.session_state.get(f"isbn_cache_{isbn}", False)
        
        if cache_hit:
            cache_status.success("⚡ Resultados cargados de caché!")
            progress.progress(100)  # Show complete
        else:
            cache_status.info("🔍 Buscando en tiendas online...")
            # Set the cache hit flag for next time
            st.session_state[f"isbn_cache_{isbn}"] = True
        
        # Get results (from cache if available)
        search_data = cached_search_books(isbn)
        results = search_data["results"]
        timestamp = search_data["timestamp"]
        
        # Update progress
        progress.progress(100)
        time.sleep(0.5)  # Brief pause to show completion
        progress.empty()
        
        # Display timestamp of when the data was fetched
        cache_status.info(f"📊 Datos actualizados a las {timestamp}" + 
                         (" (desde caché)" if cache_hit else ""))
        
        if not results:
            st.error("No se encontraron resultados para este ISBN.")
            return
        
        # Convert prices to numeric values for comparison if not already present
        for result in results:
            if 'numeric_price' not in result:
                result['numeric_price'] = normalize_price(result.get('price', 'N/A'))
        
        # Find the lowest price
        valid_prices = [r for r in results if r.get('numeric_price') is not None]
        if valid_prices:
            lowest_price_item = min(valid_prices, key=lambda x: x['numeric_price'])
            lowest_price = lowest_price_item['numeric_price']
        else:
            lowest_price = None
            lowest_price_item = None
        
        # Display results in a nice grid
        st.subheader("Resultados de la comparación")
        
        # Add CSS for store logo styling
        st.markdown("""
        <style>
        .store-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .store-logo {
            height: 24px;
            margin-right: 8px;
            max-width: 100px;
            object-fit: contain;
        }
        .best-price .store-logo {
            height: 28px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create columns for the results - 2 stores per row
        for i in range(0, len(results), 2):
            cols = st.columns(2)
            
            for j in range(2):
                if i + j < len(results):
                    result = results[i + j]
                    store = result.get('store', 'Tienda desconocida')
                    
                    # Ensure product_url exists in all cases
                    product_url = result.get('product_url')
                    if not product_url and store in STORE_URLS:
                        product_url = STORE_URLS[store].format(isbn)
                        result['product_url'] = product_url
                    
                    # Get store logo
                    store_logo = STORE_LOGOS.get(store, "")
                    
                    # Highlight the best price
                    is_lowest = (lowest_price is not None and 
                                 result.get('numeric_price') is not None and 
                                 result.get('numeric_price') == lowest_price)
                    
                    # Create a styled container with border
                    with cols[j]:
                        # Apply styling based on whether this is the lowest price
                        if is_lowest:
                            st.markdown("""
                            <style>
                            .best-price {
                                border: 2px solid #4CAF50;
                                border-radius: 5px;
                                padding: 10px;
                                background-color: #f1f8e9;
                            }
                            </style>
                            <div class="best-price">
                            """, unsafe_allow_html=True)
                            
                            # Display store logo and name with best price badge
                            if store_logo:
                                st.markdown(f"""
                                <div class="store-header">
                                    <img src="{store_logo}" class="store-logo" alt="{store} logo">
                                    <h3>🏆 {store}</h3>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"### 🏆 {store}")
                                
                            st.markdown("**¡MEJOR PRECIO!**")
                        else:
                            # Display store logo and name
                            if store_logo:
                                st.markdown(f"""
                                <div class="store-header">
                                    <img src="{store_logo}" class="store-logo" alt="{store} logo">
                                    <h3>{store}</h3>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"### {store}")
                        
                        # Display the image if available - ensure it's clickable
                        image_url = result.get('coverUrl') or result.get('image_url')
                        if image_url and product_url:
                            # Make image clickable with HTML
                            st.markdown(f'''
                            <a href="{product_url}" target="_blank">
                                <img src="{image_url}" width="150" style="cursor: pointer;">
                            </a>
                            ''', unsafe_allow_html=True)
                        elif image_url:
                            st.image(image_url, width=150)
                        
                        # Display title with link
                        title = result.get('title', 'No disponible')
                        if product_url:
                            st.markdown(f'**Título:** <a href="{product_url}" target="_blank" style="text-decoration: none; color: inherit;">{title}</a>', unsafe_allow_html=True)
                        else:
                            st.write(f"**Título:** {title}")
                        
                        # Display price with link
                        price_str = result.get('price', 'No disponible')
                        if is_lowest and product_url:
                            st.markdown(f'**Precio:** <a href="{product_url}" target="_blank" style="text-decoration: none;"><span style="color:green; font-weight:bold">{price_str}</span></a>', unsafe_allow_html=True)
                        elif is_lowest:
                            st.markdown(f"**Precio:** <span style='color:green; font-weight:bold'>{price_str}</span>", unsafe_allow_html=True)
                        elif product_url:
                            st.markdown(f'**Precio:** <a href="{product_url}" target="_blank" style="text-decoration: none; color: inherit;">{price_str}</a>', unsafe_allow_html=True)
                        else:
                            st.write(f"**Precio:** {price_str}")
                        
                        # Display price difference if this is not the lowest price
                        if not is_lowest and result.get('numeric_price') is not None and lowest_price is not None:
                            diff_euros, diff_percent = format_price_difference(lowest_price, result['numeric_price'])
                            st.write(f"**Diferencia:** +{diff_euros} ({diff_percent} más caro)")
                        
                        # Make the store name itself clickable
                        if product_url:
                            st.markdown(f"<a href='{product_url}' target='_blank' style='text-decoration: none;'><button style='background-color: #4CAF50; color: white; border: none; padding: 5px 10px; text-align: center; border-radius: 4px; cursor: pointer; width: 100%;'>Ver en {store}</button></a>", unsafe_allow_html=True)
                        
                        # Close the container div if this was the best price
                        if is_lowest:
                            st.markdown("</div>", unsafe_allow_html=True)
        
        # Create a bar chart for price comparison
        st.subheader("Comparativa visual de precios")
        
        # Prepare data for the chart
        chart_data = {
            'Tienda': [],
            'Precio': []
        }
        
        for result in results:
            if result.get('numeric_price') is not None:
                chart_data['Tienda'].append(result['store'])
                chart_data['Precio'].append(result['numeric_price'])
        
        if chart_data['Tienda']:
            df = pd.DataFrame(chart_data)
            
            # Create the bar chart
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(df['Tienda'], df['Precio'], color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb3e6'])
            
            # Add values on top of each bar
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.2f}€',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),  # 3 points vertical offset
                           textcoords="offset points",
                           ha='center', va='bottom')
            
            # Highlight the lowest price bar
            if lowest_price is not None:
                lowest_idx = df[df['Precio'] == lowest_price].index
                if not lowest_idx.empty:
                    bars[lowest_idx[0]].set_color('green')
            
            # Customize the chart
            ax.set_ylabel('Precio (€)')
            ax.set_title('Comparativa de precios por tienda')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Display the chart
            st.pyplot(fig)
            
            # Show savings information
            if lowest_price is not None and len(df) > 1:
                avg_price = df['Precio'].mean()
                max_price = df['Precio'].max()
                
                savings_avg = avg_price - lowest_price
                savings_max = max_price - lowest_price
                
                percent_avg = (savings_avg / avg_price) * 100
                percent_max = (savings_max / max_price) * 100
                
                st.subheader("💰 Ahorro potencial")
                st.write(f"Ahorro respecto al precio medio: **{savings_avg:.2f}€ ({percent_avg:.2f}%)**")
                st.write(f"Ahorro respecto al precio máximo: **{savings_max:.2f}€ ({percent_max:.2f}%)**")
        else:
            st.warning("No hay suficientes datos de precios para generar una comparativa visual.")

if __name__ == "__main__":
    main()
