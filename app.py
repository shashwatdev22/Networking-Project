from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import plotly.graph_objs as go
import networkx as nx
from fetch_functions import fetch_snmp_data, fetch_ping_results, fetch_performance_metrics, fetch_logs

app = Flask(__name__)
socketio = SocketIO(app)

def generate_network_topology(network_data, faulty_nodes, faulty_connections):
    G = nx.Graph()

    for switch, data in network_data.items():
        G.add_node(switch, label=switch)
        for neighbor, details in data['neighbors'].items():
            G.add_edge(switch, neighbor, port=details['port'], mac=details['mac'])

    pos = nx.spring_layout(G)
    edge_trace = go.Scatter(
        x=[], y=[],
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)

    node_trace = go.Scatter(
        x=[], y=[], text=[], mode='markers+text', hoverinfo='text',
        marker=dict(
            showscale=True, colorscale='YlGnBu', size=10,
            colorbar=dict(thickness=15, title='Node Connections', xanchor='left', titleside='right'),
            line_width=2
        )
    )

    for node in G.nodes():
        x, y = pos[node]
        node_trace['x'] += (x,)
        node_trace['y'] += (y,)
        hover_text = f'{node}<br>'

        if any(node == faulty_node[0] for faulty_node in faulty_nodes):
            hover_text += 'Faulty Node<br>'
        for neighbor, details in network_data[node]['neighbors'].items():
            if (node, neighbor, details['port'], details['mac']) in faulty_connections:
                hover_text += f'<br>Faulty Connection to {neighbor} via port {details["port"]} (MAC: {details["mac"]})'
            else:
                hover_text += f'<br>Connected to {neighbor} via port {details["port"]} (MAC: {details["mac"]})'
        node_trace['text'] += (hover_text,)

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title='Network Topology',
                        titlefont_size=16, showlegend=False, hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        annotations=[dict(
                            text="Network connections and device statuses",
                            showarrow=False, xref="paper", yref="paper", x=0.005, y=-0.002
                        )],
                        xaxis=dict(showgrid=False, zeroline=False),
                        yaxis=dict(showgrid=False, zeroline=False)
                    )
                )
    return fig.to_html(full_html=False)

@app.route('/')
def index():
    network_data, faulty_nodes, faulty_connections = fetch_snmp_data()
    ping_results = fetch_ping_results(network_data.keys())
    performance_metrics = fetch_performance_metrics()
    logs = fetch_logs()
    graph_html = generate_network_topology(network_data, faulty_nodes, faulty_connections)
    return render_template('dashboard.html', graph_html=graph_html, ping_results=ping_results, performance_metrics=performance_metrics, logs=logs)

@socketio.on('request_network_data')
def handle_network_data_request():
    network_data, faulty_nodes, faulty_connections = fetch_snmp_data()
    socketio.emit('network_data_update', {
        'network_data': network_data,
        'faulty_nodes': faulty_nodes,
        'faulty_connections': faulty_connections
    })

@app.route('/fetch_ping_results')
def get_ping_results():
    ping_results = fetch_ping_results()
    return jsonify(ping_results)

@app.route('/fetch_performance_metrics')
def get_performance_metrics():
    performance_metrics = fetch_performance_metrics()
    return jsonify(performance_metrics)

@app.route('/fetch_logs')
def get_logs():
    logs = fetch_logs()
    return jsonify(logs)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
