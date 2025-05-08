import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, callback, State, callback_context
from dash.exceptions import PreventUpdate

# 数据准备
df = pd.read_excel('清洗后数据2_添加编码后.xlsx', sheet_name='Sheet1')

# 数据准备
df = pd.read_excel('清洗后数据2_添加编码后.xlsx', sheet_name='Sheet1')

# 数据预处理（修正版）
def split_area(area):
    try:
        area = str(area).strip()
        if len(area) <= 2:
            return area, '', ''
        elif len(area) <= 4:
            return area[:2], area[2:], ''
        else:
            return area[:2], area[2:4], area[4:]
    except:
        return '河北', '', ''  # 关键修正：将默认值改为河北

df[['省', '市', '区县']] = df['省市'].apply(lambda x: pd.Series(split_area(x)))

# 强制保证河北存在
df['省'] = df['省'].replace('na', '河北')  # 二次修正

# 获取数量最多的3个省份（含河北）
top_provinces = df['省'].value_counts().nlargest(3).index.tolist()
if '河北' not in top_provinces:
    top_provinces.insert(0, '河北')  # 确保河北在前三

df_filtered = df[df['省'].isin(top_provinces)]
# 创建Dash应用
app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.H1("行政区域环形三级下钻分析", className="header-title"),
        html.P("仅展示数据量最大的三个省份", className="header-description"),
        html.Button("返回上级", id="back-button", className="back-button", n_clicks=0)
    ], className="header"),

    html.Div([
        html.Div(id='current-path', className="breadcrumb"),
        dcc.Graph(id='dynamic-sunburst', className="sunburst-chart")
    ], className="content"),

    dcc.Store(id='current-level', data='province'),
    dcc.Store(id='selected-province', data=None),
    dcc.Store(id='selected-city', data=None),
    dcc.Store(id='previous-state', data={'level': 'province', 'province': None, 'city': None})
])


# CSS样式和内联HTML保持不变...

# 图表生成函数
def create_province_chart(data):
    return px.sunburst(
        data,
        path=['省'],
        values='count',
        color='省',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title='',
        height=700,
        width=800,
        branchvalues='total',
        maxdepth=1
    ).update_traces(
        textinfo='label+percent parent',
        insidetextorientation='radial',
        textfont=dict(size=14),
        hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percentParent:.1%}',
        texttemplate='%{label}<br>%{percentParent:.1%}'
    )


def create_city_chart(data, province):
    return px.sunburst(
        data,
        path=['省', '市'],
        values='count',
        color='市',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title='',
        height=700,
        width=800,
        branchvalues='total',
        maxdepth=2
    ).update_traces(
        textinfo='label+percent parent',
        insidetextorientation='radial',
        textfont=dict(size=12),
        hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percentParent:.1%}',
        texttemplate='%{label}<br>%{percentParent:.1%}'
    )


def create_district_chart(data, province, city):
    return px.sunburst(
        data,
        path=['省', '市', '区县'],
        values='count',
        color='区县',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title='',
        height=700,
        width=800,
        branchvalues='total'
    ).update_traces(
        textinfo='label+percent parent',
        insidetextorientation='radial',
        textfont=dict(size=10),
        hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percentParent:.1%}',
        texttemplate='%{label}<br>%{percentParent:.1%}'
    )


# 回调函数
@app.callback(
    [Output('dynamic-sunburst', 'figure'),
     Output('current-path', 'children'),
     Output('current-level', 'data'),
     Output('selected-province', 'data'),
     Output('selected-city', 'data'),
     Output('previous-state', 'data'),
     Output('back-button', 'disabled')],
    [Input('dynamic-sunburst', 'clickData'),
     Input('back-button', 'n_clicks'),
     Input('current-path', 'n_clicks')],
    [State('current-level', 'data'),
     State('selected-province', 'data'),
     State('selected-city', 'data'),
     State('previous-state', 'data'),
     State('current-path', 'children')]
)
def update_view(clickData, back_clicks, path_clicks, current_level, selected_province, selected_city, previous_state,
                path_children):
    ctx = callback_context

    if not ctx.triggered:
        # 初始加载 - 只显示三个省份
        province_data = df_filtered.groupby('省').size().reset_index(name='count')
        fig = create_province_chart(province_data)
        path = html.Span(["当前层级：省级"])
        return fig, path, 'province', None, None, previous_state, True

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'back-button':
        # 处理返回按钮点击
        if previous_state['level'] == 'province':
            province_data = df_filtered.groupby('省').size().reset_index(name='count')
            fig = create_province_chart(province_data)
            path = html.Span(["当前层级：省级"])
            return fig, path, 'province', None, None, previous_state, True
        elif previous_state['level'] == 'city':
            city_data = df_filtered[df_filtered['省'] == previous_state['province']].groupby(
                ['省', '市']).size().reset_index(name='count')
            fig = create_city_chart(city_data, previous_state['province'])
            path = html.Span([
                html.Span(previous_state['province'], className="active-level"),
                html.I(className="fas fa-chevron-right"),
                html.Span("市级")
            ])
            new_previous = {'level': 'province', 'province': None, 'city': None}
            return fig, path, 'city', previous_state['province'], None, new_previous, False

    elif trigger_id == 'current-path' and isinstance(path_children, list):
        # 处理面包屑导航点击
        clicked_element = ctx.triggered[0]['value']
        if 'active-level' in clicked_element.get('props', {}).get('className', ''):
            label = clicked_element['props']['children']
            if current_level == 'city' and label == selected_province:
                # 点击省份名称返回省级视图
                province_data = df_filtered.groupby('省').size().reset_index(name='count')
                fig = create_province_chart(province_data)
                path = html.Span(["当前层级：省级"])
                return fig, path, 'province', None, None, previous_state, True
            elif current_level == 'district' and label == selected_city:
                # 点击城市名称返回市级视图
                city_data = df_filtered[df_filtered['省'] == selected_province].groupby(
                    ['省', '市']).size().reset_index(name='count')
                fig = create_city_chart(city_data, selected_province)
                path = html.Span([
                    html.Span(selected_province, className="active-level"),
                    html.I(className="fas fa-chevron-right"),
                    html.Span("市级")
                ])
                new_previous = {'level': 'province', 'province': None, 'city': None}
                return fig, path, 'city', selected_province, None, new_previous, False

    elif trigger_id == 'dynamic-sunburst':
        # 处理图表点击
        clicked = clickData['points'][0]['label']

        if current_level == 'province':
            # 省级下钻到市级
            city_data = df_filtered[df_filtered['省'] == clicked].groupby(['省', '市']).size().reset_index(name='count')
            if len(city_data) == 0:
                raise PreventUpdate

            fig = create_city_chart(city_data, clicked)
            path = html.Span([
                html.Span(clicked, className="active-level"),
                html.I(className="fas fa-chevron-right"),
                html.Span("市级")
            ])
            new_previous = {'level': 'province', 'province': None, 'city': None}
            return fig, path, 'city', clicked, None, new_previous, False

        elif current_level == 'city' and selected_province:
            # 市级下钻到区县级
            district_data = df_filtered[
                (df_filtered['省'] == selected_province) & (df_filtered['市'] == clicked)].groupby(
                ['省', '市', '区县']).size().reset_index(name='count')
            if len(district_data) == 0:
                raise PreventUpdate

            fig = create_district_chart(district_data, selected_province, clicked)
            path = html.Span([
                html.Span(selected_province, className="active-level"),
                html.I(className="fas fa-chevron-right"),
                html.Span(clicked, className="active-level"),
                html.I(className="fas fa-chevron-right"),
                html.Span("区县级")
            ])
            new_previous = {'level': 'city', 'province': selected_province, 'city': None}
            return fig, path, 'district', selected_province, clicked, new_previous, False

    raise PreventUpdate


if __name__ == '__main__':
    app.run(debug=True)