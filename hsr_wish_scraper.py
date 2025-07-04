import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import streamlit as st

def scrape_hsr_wish_data():
    """
    从biligame维基爬取崩坏：星穹铁道卡池信息
    """
    url = "https://wiki.biligame.com/sr/%E8%B7%83%E8%BF%81"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 定位包含卡池信息的容器
        wish_container = soup.find('div', class_='row', style='margin:0 -5px;')
        
        if not wish_container:
            st.error("未找到卡池信息容器")
            return []
            
        # 找到所有卡池表格
        wish_tables = wish_container.find_all('table', class_='wikitable')
        
        wish_data = []
        
        for table in wish_tables:
            wish_info = {}
            
            # 提取时间 - 更健壮的提取方法
            time_th = table.find('th', string='时间')
            if not time_th:
                time_th = table.find('th', string=re.compile(r'时间'))
            if time_th:
                time_td = time_th.find_next('td')
                if time_td:
                    wish_info['时间'] = time_td.get_text(strip=True).replace('\n', ' ').replace('\t', '')
            
            # 提取版本 - 更健壮的提取方法
            version_th = table.find('th', string='版本')
            if not version_th:
                version_th = table.find('th', string=re.compile(r'版本'))
            if version_th:
                version_td = version_th.find_next('td')
                if version_td:
                    wish_info['版本'] = version_td.get_text(strip=True).replace('\n', ' ').replace('\t', '')
            
            # 提取5星角色/光锥
            star5_row = table.find('th', string=re.compile(r'5星(角色|光锥)'))
            if star5_row:
                star5_type = "角色" if "角色" in star5_row.get_text() else "光锥"
                star5_td = star5_row.find_next('td')
                if star5_td:
                    # 提取名称和属性/类型
                    star5_text = star5_td.get_text(strip=True)
                    # 移除图片和多余空格
                    star5_text = re.sub(r'\s+', ' ', star5_text)
                    wish_info['5星类型'] = star5_type
                    wish_info['5星内容'] = star5_text
            
            # 提取4星角色/光锥
            star4_row = table.find('th', string=re.compile(r'4星(角色|光锥)'))
            if star4_row:
                star4_type = "角色" if "角色" in star4_row.get_text() else "光锥"
                star4_td = star4_row.find_next('td')
                if star4_td:
                    # 提取所有4星内容
                    star4_items = []
                    # 处理包含多个项目的行（使用<br>分隔）
                    for item in star4_td.children:
                        if item.name == 'br':
                            continue
                        if item.name == 'a':
                            item_text = item.get_text(strip=True)
                            if item_text:
                                star4_items.append(item_text)
                        elif isinstance(item, str) and item.strip():
                            star4_items.append(item.strip())
                    
                    # 如果没有找到单独的项目，则直接提取文本
                    if not star4_items:
                        star4_text = star4_td.get_text(strip=True)
                        # 分割多行文本
                        star4_items = [s.strip() for s in star4_text.split('\n') if s.strip()]
                    
                    wish_info['4星类型'] = star4_type
                    wish_info['4星内容'] = ", ".join(star4_items)
            
            # 确定卡池类型
            if '5星类型' in wish_info:
                wish_info['卡池类型'] = "角色池" if wish_info['5星类型'] == "角色" else "光锥池"
                wish_data.append(wish_info)
        
        return wish_data
    
    except Exception as e:
        st.error(f"爬取数据时出错: {str(e)}")
        return []

def format_wish_data(wish_data):
    """
    格式化卡池数据用于展示
    """
    formatted_data = []
    
    for wish in wish_data:
        # 提取卡池版本 - 更健壮的提取方法
        version = wish.get('版本', '未知版本')
        version_match = re.search(r'(\d+\.\d+)(?:[^\d]*(\d+))?', version)
        if version_match:
            # 拼接版本号，如 "3.4" + "1" = "3.41"
            version = version_match.group(1)
            if version_match.group(2):
                version += '.' + version_match.group(2)
        else:
            # 尝试从5星内容中提取版本
            version_match = re.search(r'(\d+\.\d+)', wish.get('5星内容', ''))
            version = version_match.group(1) if version_match else "未知版本"
        
        # 格式化时间 - 更健壮的处理
        time_str = wish.get('时间', '时间未知')
        # 清理时间格式
        time_str = re.sub(r'[^\d~/\-年月日时分:后至]', '', time_str)
        time_str = time_str.replace('后', '开始').replace('~', ' 至 ')
        
        # 提取5星内容（移除可能存在的属性信息）
        star5_content = re.sub(r'（.*?）', '', wish.get('5星内容', '未知'))
        
        formatted_data.append({
            "版本": version,
            "卡池类型": wish.get('卡池类型', '未知'),
            "时间": time_str,
            "5星内容": star5_content,
            "4星内容": wish.get('4星内容', ''),
            "原始数据": wish  # 保留原始数据用于调试
        })
    
    return formatted_data

def display_wish_data(formatted_data):
    """
    在Streamlit中展示卡池数据
    """
    st.title("崩坏：星穹铁道卡池信息")
    st.markdown("""
    <style>
    .wish-card {
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #2a2d3e;
        color: #ffffff;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        border-left: 5px solid #7b68ee;
    }
    .character-pool {
        border-left-color: #ff6b6b;
    }
    .lightcone-pool {
        border-left-color: #48dbfb;
    }
    .wish-name {
        font-size: 1.5rem;
        font-weight: bold;
        color: #ffd700;
        margin-bottom: 10px;
    }
    .wish-version {
        background-color: #7b68ee;
        color: white;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 0.9rem;
        margin-left: 10px;
    }
    .wish-time {
        font-size: 1rem;
        margin-bottom: 10px;
        color: #a9a9a9;
        padding: 8px;
        background-color: #3a3d4e;
        border-radius: 5px;
    }
    .wish-char-5 {
        font-size: 1.3rem;
        font-weight: bold;
        color: #ffd700;
        margin: 10px 0;
    }
    .wish-char-4 {
        font-size: 1.1rem;
        color: #c0c0c0;
        margin: 5px 0;
    }
    .pool-type {
        font-size: 0.9rem;
        background-color: #6a89cc;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        display: inline-block;
        margin-left: 10px;
    }
    .character-type {
        background-color: #ff6b6b;
    }
    .lightcone-type {
        background-color: #48dbfb;
    }
    .info-grid {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 8px;
        margin-bottom: 15px;
        background-color: #3a3d4e;
        padding: 10px;
        border-radius: 8px;
    }
    .info-label {
        font-weight: bold;
        color: #ffd700;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 显示当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"数据更新时间: {current_time} | 来源: biligame维基")
    
    # 按卡池类型分组
    character_pools = [w for w in formatted_data if w['卡池类型'] == '角色池']
    lightcone_pools = [w for w in formatted_data if w['卡池类型'] == '光锥池']
    
    # 显示角色池
    st.subheader("角色活动跃迁")
    for wish in character_pools:
        pool_class = "character-pool"
        pool_type_class = "character-type"
        
        with st.container():
            st.markdown(f"""
            <div class="wish-card {pool_class}">
                <div>
                    <span class="wish-name">{wish['5星内容']}</span>
                    <span class="wish-version">v{wish['版本']}</span>
                    <span class="pool-type {pool_type_class}">角色池</span>
                </div>
                
                <div class="info-grid">
                    <div class="info-label">活动时间：</div>
                    <div class="wish-time">⏰ {wish['时间']}</div>
                </div>
                
                <div class="wish-char-5">★★★★★ {wish['5星内容']}</div>
                <div class="wish-char-4">★★★★ {wish['4星内容']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # 显示光锥池
    st.subheader("光锥活动跃迁")
    for wish in lightcone_pools:
        pool_class = "lightcone-pool"
        pool_type_class = "lightcone-type"
        
        with st.container():
            st.markdown(f"""
            <div class="wish-card {pool_class}">
                <div>
                    <span class="wish-name">{wish['5星内容']}</span>
                    <span class="wish-version">v{wish['版本']}</span>
                    <span class="pool-type {pool_type_class}">光锥池</span>
                </div>
                
                <div class="info-grid">
                    <div class="info-label">活动时间：</div>
                    <div class="wish-time">⏰ {wish['时间']}</div>
                </div>
                
                <div class="wish-char-5">★★★★★ {wish['5星内容']}</div>
                <div class="wish-char-4">★★★★ {wish['4星内容']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # 显示数据表格
    st.subheader("所有卡池数据")
    df = pd.DataFrame(formatted_data)
    
    # 只保留需要的列
    df = df[['版本', '卡池类型', '时间', '5星内容', '4星内容']]
    
    # 重命名列
    df.columns = ['版本', '卡池类型', '活动时间', '5星UP', '4星UP']
    
    # 设置样式
    def highlight_pool_type(row):
        if row['卡池类型'] == '角色池':
            return ['background-color: #ffebee'] * len(row)
        elif row['卡池类型'] == '光锥池':
            return ['background-color: #e3f2fd'] * len(row)
        return [''] * len(row)
    
    styled_df = df.style.apply(highlight_pool_type, axis=1)
    st.dataframe(styled_df, use_container_width=True)

# 主程序
def main():
    st.set_page_config(
        page_title="崩坏：星穹铁道卡池信息",
        page_icon="⭐",
        layout="wide"
    )
    
    with st.spinner("正在获取卡池信息..."):
        raw_data = scrape_hsr_wish_data()
        if not raw_data:
            st.error("未能获取卡池信息，请稍后再试")
            return
            
        formatted_data = format_wish_data(raw_data)
        
    if not formatted_data:
        st.error("没有解析到有效的卡池数据")
        return
        
    display_wish_data(formatted_data)

if __name__ == "__main__":
    main()