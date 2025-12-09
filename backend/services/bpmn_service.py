import xml.etree.ElementTree as ET
import pandas as pd
from collections import defaultdict
import re
import html

class BPMNProcessor:
    def __init__(self):
        self.ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        self.resource_map = {}
        self.elements = {}
        self.element_types = {}
        self.node_raw_tags = {}
        self.lanes = {}
        self.descriptions = {}
        self.explicit_roles = {}
        self.graph = defaultdict(list)
        self.all_data = []

    def _clean_html(self, raw_html):
        if not raw_html: return ""
        text = html.unescape(raw_html)
        text = re.sub(r'<[^>]+>', ' ', text)
        return " ".join(text.split())

    def _extract_resources(self, root):
        """Extrae los recursos (roles) del XML."""
        self.resource_map = {}
        for elem in root.iter():
            if elem.tag.endswith('resource'):
                r_id = elem.get('id')
                r_name = elem.get('name')
                if r_id and r_name:
                    self.resource_map[r_id] = r_name

    def _parse_elements(self, process):
        """Parsea nodos, lanes y documentación de un proceso."""
        # A. Lanes
        for lane in process.iter():
            if lane.tag.endswith('lane'):
                lane_name = lane.get('name')
                for ref in lane.iter():
                    if ref.tag.endswith('flowNodeRef') and ref.text:
                        self.lanes[ref.text.strip()] = lane_name

        # B. Nodos
        for node in process.iter():
            tag_clean = node.tag.split('}')[-1]
            nid = node.get('id')
            if not nid: continue
            
            self.node_raw_tags[nid] = tag_clean

            if 'Task' in tag_clean: e_type = 'Tarea'
            elif 'Gateway' in tag_clean: e_type = 'Compuerta'
            elif 'startEvent' in tag_clean: e_type = 'Inicio'
            elif 'endEvent' in tag_clean: e_type = 'Fin'
            elif 'Event' in tag_clean: e_type = 'Evento'
            else: continue 

            self.elements[nid] = node.get('name', '')
            self.element_types[nid] = e_type
            
            # Descripción
            for child in node:
                if child.tag.endswith('documentation') and child.text:
                    self.descriptions[nid] = child.text

            # Rol Explícito
            if 'Task' in tag_clean:
                found_role = None
                for subchild in node.iter():
                    if subchild.text:
                        candidate_id = subchild.text.strip().split(':')[-1]
                        if candidate_id in self.resource_map:
                            found_role = self.resource_map[candidate_id]
                            break
                if found_role: self.explicit_roles[nid] = found_role

        # C. Conexiones iniciales
        for seq in process.iter():
            if seq.tag.endswith('sequenceFlow'):
                s = seq.get('sourceRef')
                t = seq.get('targetRef')
                if s and t: self.graph[s].append(t)

    def _traverse_flow(self, node_id, visited, process_name, order_counter, flow_group_id):
        """Función recursiva DFS para recorrer el grafo."""
        if node_id in visited: return order_counter
        visited.add(node_id)
        
        # Datos básicos
        name = self.elements.get(node_id, '')
        e_type = self.element_types.get(node_id, 'Desconocido')
        clean_desc = self._clean_html(self.descriptions.get(node_id, ''))
        
        # Rol
        role = self.explicit_roles.get(node_id)
        if not role: role = self.lanes.get(node_id)
        if not role: role = 'Sistema / General'

        # Guardar en lista temporal
        if name or e_type in ['Inicio', 'Fin', 'Compuerta', 'Tarea']:
            clean_name = name.replace('\n', ' ').strip()
            self.all_data.append({
                'Proceso Principal': process_name,
                'Sub-Flujo': flow_group_id,
                'Orden_Tecnico': order_counter,
                'Rol (Responsable)': role,
                'Actividad': clean_name,
                'Descripción': clean_desc,
                'Tipo': e_type,
                'ID': node_id
            })
            order_counter += 1

        # Siguientes pasos
        for next_node in self.graph.get(node_id, []):
            order_counter = self._traverse_flow(next_node, visited, process_name, order_counter, flow_group_id)
        
        return order_counter

    def process_xml(self, xml_file):
        """Método principal para procesar el archivo XML."""
        self.all_data = [] # Reset data
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
        except Exception as e:
            return None, f"Error al leer el archivo XML: {e}"

        self._extract_resources(root)
        
        processes = [p for p in root.iter() if p.tag.endswith('process')]

        for process in processes:
            process_name = process.get('name', 'Proceso Sin Nombre')
            
            # Resetear estructuras por proceso
            self.elements = {}
            self.element_types = {}
            self.node_raw_tags = {}
            self.lanes = {}
            self.descriptions = {}
            self.explicit_roles = {}
            self.graph = defaultdict(list)

            # 1. Parsear elementos base
            self._parse_elements(process)

            # 2. Lógica de Desconexión Virtual (Catch -> Converging)
            # Calcular In-Degree
            incoming_count = defaultdict(int)
            for src, targets in self.graph.items():
                for t in targets:
                    incoming_count[t] += 1
            
            # Identificar Gateways
            gateways_to_isolate = set()
            for src_id, targets in self.graph.items():
                src_tag = self.node_raw_tags.get(src_id, '')
                if 'intermediateCatchEvent' in src_tag:
                    for target_id in targets:
                        target_tag = self.node_raw_tags.get(target_id, '')
                        if 'Gateway' in target_tag and incoming_count[target_id] > 1:
                            gateways_to_isolate.add(target_id)

            # Aplicar corte y guardar prioridades
            priority_restart_nodes = []
            for g_id in gateways_to_isolate:
                if g_id in self.graph:
                    removed_targets = self.graph[g_id]
                    priority_restart_nodes.extend(removed_targets)
                    self.graph[g_id] = [] # Corte virtual

            # 3. Ejecución DFS
            visited = set()
            start_nodes = [n for n, t in self.element_types.items() if t == 'Inicio']
            
            # A. Flujo Principal
            for start_node in start_nodes:
                if start_node not in visited:
                    start_name = self.elements.get(start_node, 'Flujo Principal')
                    self._traverse_flow(start_node, visited, process_name, 1, start_name)

            # B. Puntos de Reinicio Prioritarios (Post-Converging)
            for p_node in priority_restart_nodes:
                if p_node not in visited:
                    self._traverse_flow(p_node, visited, process_name, 1, "Continuación Post-Gateway")

            # C. Huérfanos Generales
            all_ids = set(self.elements.keys())
            unvisited = all_ids - visited
            while unvisited:
                sub_graph_targets = {t for src, tgts in self.graph.items() if src in unvisited for t in tgts}
                roots = list(unvisited - sub_graph_targets)
                root_node = roots[0] if roots else list(unvisited)[0]
                
                self._traverse_flow(root_node, visited, process_name, 1, "Otros Flujos")
                unvisited = all_ids - visited

        # Generar DataFrame
        if self.all_data:
            df = pd.DataFrame(self.all_data)
            df_tareas = df[df['Tipo'] == 'Tarea'].copy()
            df_tareas['Orden_Reporte'] = range(1, len(df_tareas) + 1)
            
            cols_finales = [
                'Orden_Reporte', 'ID', 'Actividad', 
                'Descripción', 'Rol (Responsable)', 'Proceso Principal'
            ]
            return df_tareas[cols_finales], None
        else:
            return pd.DataFrame(), "No se encontraron datos procesables."