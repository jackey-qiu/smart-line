from PyQt5.QtGui import QPaintEvent, QPainter, QPen
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from ...widgets.shapes.shape_container import rectangle, shapeComposite, isocelesTriangle, buildTools
from ....util.util import findMainWindow

class queueSynopticView(QWidget):
    FILL_QUEUED = {'brush': {'color': (0, 0, 255)}}
    FILL_RUN = {'brush': {'color': (50, 255, 0)}}
    FILL_DISABLED = {'brush': {'color': (50, 50, 50)}}
    FILL_FAILED = {'brush': {'color': (255, 50, 0)}}
    FILL_PAUSED = {'brush': {'color': (255, 0, 255)}}
    CLICKED_SHAPE = {'pen': {'color': (255, 255, 0), 'width': 3, 'ls': 'SolidLine'}}
    NONCLICKED_SHAPE = {'pen': {'color': (255, 0, 0), 'width': 3, 'ls': 'SolidLine'}}

    def __init__(self, parent = None, padding_vertical = 20, padding_hor = 60, block_width=180, block_height =20) -> None:
        super().__init__(parent = parent)
        self.set_parent()
        self.padding_vertical = padding_vertical
        self.padding_hor = padding_hor
        self.block_width = block_width
        self.block_height = block_height
        self._data = []
        self.composite_shape_container = {}
        self.composite_shapes = []
        self.legend_shapes = []
        self.last_clicked_shape = None
        self.lines_bw_composite = []
        self.triangle_ends = []

    def set_data(self, data):
        self._data = data
        self.build_shapes()
        self.build_legend_shapes()

    def _calculate_col_num_blocks(self):
        widget_height = self.size().height()
        widget_width = self.size().width()
        num_blocks_each_column = int((widget_height - widget_height%(self.padding_vertical + self.block_height))/(self.padding_vertical + self.block_height))
        return num_blocks_each_column

    def build_legend_shapes(self):
        height = 20
        width = int(self.padding_hor*0.8)
        x = int(self.padding_hor*0.1)
        shape_queued = rectangle(dim=[x, self.padding_vertical, width, height])
        shape_queued.decoration = self.FILL_QUEUED
        shape_queued.labels = {'text':['queued'],'anchor':['center']}
        shape_disabled = rectangle(dim=[x, (self.padding_vertical + self.block_height)*1+self.padding_vertical, width, height])
        shape_disabled.decoration = self.FILL_DISABLED
        shape_disabled.labels = {'text':['disabled'],'anchor':['center']}
        shape_failed = rectangle(dim=[x, (self.padding_vertical+ self.block_height)*2+self.padding_vertical, width, height])
        shape_failed.decoration = self.FILL_FAILED
        shape_failed.labels = {'text':['failed'],'anchor':['center']}
        shape_pause = rectangle(dim=[x, (self.padding_vertical+ self.block_height)*3+self.padding_vertical, width, height])
        shape_pause.decoration = self.FILL_PAUSED
        shape_pause.labels = {'text':['pause'],'anchor':['center']}
        shape_run = rectangle(dim=[x, (self.padding_vertical+ self.block_height)*4+self.padding_vertical, width, height])
        shape_run.decoration = self.FILL_RUN
        shape_run.labels = {'text':['run'],'anchor':['center']}
        self.legend_shapes = [shape_queued, shape_disabled, shape_failed, shape_pause, shape_run]
        
    def build_shapes(self):
        self.composite_shape_container = {}
        if len(self._data)==0:
            self.shapes = []
            return
        size_col = self._calculate_col_num_blocks()
        for i in range(len(self._data)):
            which_col = int((i+1)/size_col)
            shape = rectangle(dim = [self.padding_hor + which_col*(self.block_width + self.padding_hor),self.padding_vertical,self.block_width,self.block_height],rotation_center = None, transformation={'rotate':0, 'translate':(0,0), 'scale':1})
            state = self._data.iloc[i,:]['state']
            unique_id = self._data.iloc[i,:]['unique_id']
            cmd = self._data.iloc[i,:]['scan_command']
            if state == 'queued':
                shape.decoration = self.FILL_QUEUED
                shape.decoration_cursor_off = self.FILL_QUEUED
                shape.decoration_cursor_on = self.FILL_QUEUED
            elif state == 'running':
                shape.decoration = self.FILL_RUN
                shape.decoration_cursor_off = self.FILL_RUN
                shape.decoration_cursor_on = self.FILL_RUN
            elif state == 'failed':
                shape.decoration = self.FILL_FAILED
                shape.decoration_cursor_off = self.FILL_FAILED
                shape.decoration_cursor_on = self.FILL_FAILED
            elif state == 'paused':
                shape.decoration = self.FILL_PAUSED
                shape.decoration_cursor_off = self.FILL_PAUSED
                shape.decoration_cursor_on = self.FILL_PAUSED
            elif state == 'disabled':
                shape.decoration = self.FILL_DISABLED
                shape.decoration_cursor_off = self.FILL_DISABLED
                shape.decoration_cursor_on = self.FILL_DISABLED
            shape.labels = {'text':[f'{cmd}'],'anchor':['center']}
            setattr(shape, 'unique_id', unique_id)
            if which_col not in self.composite_shape_container:
                self.composite_shape_container[which_col] = []
                self.composite_shape_container[which_col].append(shape)
            else:
                self.composite_shape_container[which_col].append(shape)
        self.build_composite_object()
        self.update()

    def build_composite_object(self):
        self.composite_shapes = []
        self.lines_bw_composite = []
        self.triangle_ends = []
        for each, shapes in self.composite_shape_container.items():
            composite = shapeComposite(shapes = shapes, \
                                             anchor_args = [4 for i in range(len(shapes))], \
                                             alignment_pattern= {'shapes':[[i, i+1] for i in range(len(shapes)-1)], \
                                                                 'anchors':[['bottom', 'top'] for i in range(len(shapes)-1)],\
                                                                 'gaps': [self.padding_vertical/self.block_height for i in range(len(shapes)-1)],\
                                                                 'ref_anchors': [['bottom', 'top'] for i in range(len(shapes)-1)],\
                                                                },
                                             connection_pattern= {'shapes':[[i, i+1] for i in range(len(shapes)-1)], \
                                                                 'anchors':[['bottom', 'top'] for i in range(len(shapes)-1)], \
                                                                 'connect_types':[True for i in range(len(shapes)-1)] })
            self.composite_shapes.append(composite)
        #make line connection between two adjacent composit shapes
        for i in range(len(self.composite_shapes)-1):
            shapes = [self.composite_shapes[i].shapes[-1], self.composite_shapes[i+1].shapes[0]]
            anchors = ['right', 'left']
            rot_cen = [shapes[-1].dim_pars[0], shapes[-1].dim_pars[1]+int(shapes[-1].dim_pars[-1]/2)]
            self.triangle_ends.append(isocelesTriangle(dim = rot_cen + [10, 60]))
            self.triangle_ends[-1].transformation = {'rotate':90}
            self.triangle_ends[-1].rot_center = rot_cen
            self.triangle_ends[-1].decoration = {'pen': {'color': (0, 255, 0), 'width': 2, 'ls': 'SolidLine'}, 'brush': {'color': (0, 255, 0)}} 
            self.lines_bw_composite.append(buildTools.make_line_connection_btw_two_anchors(shapes, anchors, short_head_line_len = int(self.padding_hor/2), direct_connection = True))

    # def set_parent(self, parent):
        # self.parent = parent

    def set_parent(self):
        self.parent = findMainWindow()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        qp = QPainter()
        qp.begin(self)
        # for each in self.shapes:            
        for each in self.composite_shapes:
            for line in each.lines:
                qp.setPen(QPen(Qt.green, 2, Qt.SolidLine))        
                for i in range(len(line)-1):
                    pts = list(line[i]) + list(line[i+1])
                    qp.drawLine(*pts)  
        for line in self.lines_bw_composite:
            qp.setPen(QPen(Qt.green, 2, Qt.SolidLine))        
            for i in range(len(line)-1):
                pts = list(line[i]) + list(line[i+1])
                qp.drawLine(*pts)              
        for each in self.composite_shapes:
            for each_shape in each.shapes:
                qp.resetTransform()
                each_shape.paint(qp)
        for each_shape in self.triangle_ends:
            qp.resetTransform()
            each_shape.paint(qp)
        for each_shape in self.legend_shapes:
            qp.resetTransform()
            each_shape.paint(qp)
        qp.end()

    def mouseMoveEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()
        # if self.parent !=None:
            # self.parent.statusbar.showMessage('Mouse coords: ( %d : %d )' % (event.x(), event.y()))
        for each in self.composite_shapes:
            for each_shape in each.shapes:
                each_shape.cursor_pos_checker(event.x(), event.y())
        self.update()

    def mousePressEvent(self, event):
        x, y = event.x(), event.y()
        shapes_under_cursor = []
        for each in self.composite_shapes:
            for each_shape in each.shapes:
                if each_shape.check_pos(x, y) and event.button() == Qt.LeftButton:
                    # queue_id = each_shape.labels['text'][0].rsplit(':')[0]
                    unique_id = each_shape.unique_id
                    self.parent.update_task_from_server(unique_id)
                    if self.parent !=None:
                        self.parent.statusbar.showMessage(f'Clicked job id is: {unique_id}')
                    if self.last_clicked_shape==None:
                        #self.last_clicked_shape.decoration_cursor_off = self.NONCLICKED_SHAPE
                        self.last_clicked_shape = each_shape
                        self.last_clicked_shape.decoration_cursor_off = self.CLICKED_SHAPE
                    else:
                        self.last_clicked_shape.decoration_cursor_off = self.NONCLICKED_SHAPE
                        self.last_clicked_shape = each_shape
                        self.last_clicked_shape.decoration_cursor_off = self.CLICKED_SHAPE
                    return