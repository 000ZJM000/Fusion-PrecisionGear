#Author-YourName
#Description-Draws an optimized involute gear profile (With Origin, Backlash, and Tip Fillet).

import adsk.core, adsk.fusion, adsk.cam, traceback
import math

# 全局变量保持引用
_handlers = []

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        # 清理旧命令
        cmdDef = ui.commandDefinitions.itemById('cmdAdvancedGearFillet')
        if cmdDef:
            cmdDef.deleteMe()

        cmdDef = ui.commandDefinitions.addButtonDefinition('cmdAdvancedGearFillet', '绘制高级齿轮(全功能)', '包含原点选择、间隙、齿根及齿顶倒角', '')

        onCommandCreated = GearCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        cmdDef.execute()
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        cmdDef = ui.commandDefinitions.itemById('cmdAdvancedGearFillet')
        if cmdDef:
            cmdDef.deleteMe()
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class GearCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs
            
            # --- 默认参数 ---
            defaultModule = 2.0  
            defaultTeeth = 20
            defaultPressureAngle = 20.0 
            defaultShift = 0.0 
            defaultAddendumFactor = 1.0 
            defaultClearanceFactor = 0.25 
            defaultBacklash = 0.1 
            defaultRootFillet = 0.2
            defaultTipFillet = 0.0

            # --- 创建UI ---
            
            # 0. 选择原点
            selInput = inputs.addSelectionInput('centerPoint', '中心点 (可选)', '选择一个点作为齿轮中心，不选则默认为原点')
            selInput.addSelectionFilter('SketchPoints') 
            selInput.addSelectionFilter('ConstructionPoints') 
            selInput.addSelectionFilter('Vertices') 
            selInput.setSelectionLimits(0, 1) 

            # 1. 模数
            inputs.addValueInput('module', '模数 (m)', 'mm', adsk.core.ValueInput.createByReal(defaultModule / 10.0)) 
            
            # 2. 齿数
            inputs.addIntegerSpinnerCommandInput('teeth', '齿数 (z)', 3, 500, 1, defaultTeeth)
            
            # 3. 压力角
            inputs.addValueInput('pressureAngle', '压力角 (α)', 'deg', adsk.core.ValueInput.createByReal(math.radians(defaultPressureAngle)))
            
            # 4. 变位系数
            inputs.addValueInput('shift', '变位系数 (x)', '', adsk.core.ValueInput.createByReal(defaultShift))
            
            # 5. 装配间隙
            inputs.addValueInput('backlash', '齿厚减薄/间隙 (j)', 'mm', adsk.core.ValueInput.createByReal(defaultBacklash / 10.0))

            # 6. 齿顶高系数
            inputs.addValueInput('addendumFactor', '齿顶高系数 (ha*)', '', adsk.core.ValueInput.createByReal(defaultAddendumFactor))
            
            # 7. 齿根系数        
            inputs.addValueInput('clearanceFactor', '顶隙系数 (c*)', '', adsk.core.ValueInput.createByReal(defaultClearanceFactor))

            # 8. 齿根倒角半径     
            inputs.addValueInput('rootFillet', '齿根倒角半径 (Rf)', 'mm', adsk.core.ValueInput.createByReal(defaultRootFillet / 10.0))
            
            # 9. 齿顶倒角半径    
            inputs.addValueInput('tipFillet', '齿顶倒角半径 (Rt)', 'mm', adsk.core.ValueInput.createByReal(defaultTipFillet / 10.0))

            onExecute = GearCommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)
        except:
            if adsk.core.Application.get().userInterface:
                adsk.core.Application.get().userInterface.messageBox('UI Error:\n{}'.format(traceback.format_exc()))

class GearCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface
            
            if not app.activeEditObject or not isinstance(app.activeEditObject, adsk.fusion.Sketch):
                ui.messageBox('错误：请先创建并进入一个草图的编辑模式。')
                return

            sketch = app.activeEditObject
            inputs = args.command.commandInputs

            # --- 获取几何参数 ---
            mod = inputs.itemById('module').value 
            z = inputs.itemById('teeth').value
            alpha = inputs.itemById('pressureAngle').value 
            x = inputs.itemById('shift').value
            backlash = inputs.itemById('backlash').value 
            
            ha_star = inputs.itemById('addendumFactor').value
            c_star = inputs.itemById('clearanceFactor').value
            
            root_fillet_r = inputs.itemById('rootFillet').value 
            tip_fillet_r = inputs.itemById('tipFillet').value 

            # --- 获取中心点 ---
            center_geo = adsk.core.Point3D.create(0, 0, 0)
            sel_input = inputs.itemById('centerPoint')
            
            if sel_input.selectionCount > 0:
                ent = sel_input.selection(0).entity
                world_point = None
                if hasattr(ent, 'worldGeometry'): world_point = ent.worldGeometry
                elif hasattr(ent, 'geometry'): world_point = ent.geometry
                
                if world_point:
                    center_geo = sketch.modelToSketchSpace(world_point)

            self.draw_gear(sketch, center_geo, mod, z, alpha, x, backlash, ha_star, c_star, root_fillet_r, tip_fillet_r)

        except:
            if adsk.core.Application.get().userInterface:
                adsk.core.Application.get().userInterface.messageBox('Execute Failed:\n{}'.format(traceback.format_exc()))

    def draw_gear(self, sketch, center_pt, mod, z, alpha, x, backlash, ha_star, c_star, root_fillet_r, tip_fillet_r):
        sketch.isComputeDeferred = True 
        
        splines = sketch.sketchCurves.sketchFittedSplines
        lines = sketch.sketchCurves.sketchLines
        arcs = sketch.sketchCurves.sketchArcs

        # --- A. 基础几何计算 (cm) ---
        r_pitch = (mod * z) / 2.0
        r_base = r_pitch * math.cos(alpha)
        r_tip = r_pitch + mod * (ha_star + x)
        r_root = r_pitch - mod * (ha_star + c_star - x)

        inv_alpha = math.tan(alpha) - alpha
        
        angle_half_thick_pitch = (math.pi / (2.0 * z)) + (2.0 * x * math.tan(alpha) / z)
        angle_reduction_per_side = (backlash / 2.0) / r_pitch
        angle_half_thick_pitch -= angle_reduction_per_side

        angle_pitch = 2.0 * math.pi / z
        angle_to_root_mid = angle_pitch / 2.0 

        # --- B. 计算单个齿的关键点 (相对于 0,0) ---
        
        def get_inv_point(r_curr, is_right):
            if r_curr <= r_base: alpha_r = 0.0
            else: alpha_r = math.acos(r_base / r_curr)
            inv_r = math.tan(alpha_r) - alpha_r
            delta = angle_half_thick_pitch + inv_alpha - inv_r
            angle = (math.pi/2.0) - delta if is_right else (math.pi/2.0) + delta
            return adsk.core.Point3D.create(r_curr * math.cos(angle), r_curr * math.sin(angle), 0)

        base_points_left = []
        base_points_right = []
        num_points = 5 
        start_r_inv = max(r_base, r_root)
        
        for i in range(num_points + 1):
            r_curr = start_r_inv + (r_tip - start_r_inv) * (i / float(num_points))
            base_points_left.append(get_inv_point(r_curr, False))
            base_points_right.append(get_inv_point(r_curr, True))

        pt_tip_mid = adsk.core.Point3D.create(0, r_tip, 0)

        # Undercut logic
        has_undercut = r_base > (r_root + 0.001)
        pt_root_left_undercut = None
        pt_root_right_undercut = None

        if has_undercut:
            p0 = base_points_left[0]
            ang = math.atan2(p0.y, p0.x)
            pt_root_left_undercut = adsk.core.Point3D.create(r_root*math.cos(ang), r_root*math.sin(ang), 0)
            p0 = base_points_right[0]
            ang = math.atan2(p0.y, p0.x)
            pt_root_right_undercut = adsk.core.Point3D.create(r_root*math.cos(ang), r_root*math.sin(ang), 0)

        # Root mid points
        ang_root_mid_l = (math.pi/2.0) + angle_to_root_mid
        pt_root_mid_l = adsk.core.Point3D.create(r_root*math.cos(ang_root_mid_l), r_root*math.sin(ang_root_mid_l), 0)
        ang_root_mid_r = (math.pi/2.0) - angle_to_root_mid
        pt_root_mid_r = adsk.core.Point3D.create(r_root*math.cos(ang_root_mid_r), r_root*math.sin(ang_root_mid_r), 0)

        # --- C. 变换函数 ---
        def transform_pt(pt, theta):
            c = math.cos(theta)
            s = math.sin(theta)
            x_rot = pt.x * c - pt.y * s
            y_rot = pt.x * s + pt.y * c
            return adsk.core.Point3D.create(x_rot + center_pt.x, y_rot + center_pt.y, 0)

        def transform_points(pts, theta):
            return [transform_pt(p, theta) for p in pts]

        # --- D. 循环绘制 ---
        for i in range(z):
            theta = i * angle_pitch 

            # 1. 坐标变换
            curr_pts_left = transform_points(base_points_left, theta)
            curr_pts_right = transform_points(base_points_right, theta)
            curr_pt_tip = transform_pt(pt_tip_mid, theta)
            
            curr_root_mid_l = transform_pt(pt_root_mid_l, theta)
            curr_root_mid_r = transform_pt(pt_root_mid_r, theta)

            # 2. 渐开线
            coll_l = adsk.core.ObjectCollection.create()
            for p in curr_pts_left: coll_l.add(p)
            spline_l = splines.add(coll_l)

            coll_r = adsk.core.ObjectCollection.create()
            for p in curr_pts_right: coll_r.add(p)
            spline_r = splines.add(coll_r)

            # 3. 齿顶圆弧
            # 捕获端点用于倒角猜测
            tip_corner_l = spline_l.endSketchPoint.geometry
            tip_corner_r = spline_r.endSketchPoint.geometry
            
            arc_tip = arcs.addByThreePoints(spline_l.endSketchPoint, curr_pt_tip, spline_r.endSketchPoint)

            # 齿顶倒角 (Tip Fillet)
            if tip_fillet_r > 0.001:
                try:
                    # 左侧齿顶倒角
                    arcs.addFillet(spline_l, tip_corner_l, arc_tip, tip_corner_l, tip_fillet_r)
                except: pass

                try:
                    # 右侧齿顶倒角
                    arcs.addFillet(spline_r, tip_corner_r, arc_tip, tip_corner_r, tip_fillet_r)
                except: pass

            # 4. 根部连接
            leg_l_end = spline_l.startSketchPoint
            leg_r_end = spline_r.startSketchPoint
            
            obj_for_fillet_l = spline_l 
            obj_for_fillet_r = spline_r

            if has_undercut:
                curr_undercut_l = transform_pt(pt_root_left_undercut, theta)
                curr_undercut_r = transform_pt(pt_root_right_undercut, theta)
                
                line_l = lines.addByTwoPoints(leg_l_end, curr_undercut_l)
                line_r = lines.addByTwoPoints(leg_r_end, curr_undercut_r)
                
                leg_l_end = line_l.endSketchPoint
                leg_r_end = line_r.endSketchPoint
                
                obj_for_fillet_l = line_l 
                obj_for_fillet_r = line_r

            # 5. 根部圆弧
            ang_start_l = math.atan2(leg_l_end.geometry.y - center_pt.y, leg_l_end.geometry.x - center_pt.x)
            ang_end_l = math.atan2(curr_root_mid_l.y - center_pt.y, curr_root_mid_l.x - center_pt.x)
            
            diff = ang_end_l - ang_start_l
            while diff <= -math.pi: diff += 2*math.pi
            while diff > math.pi: diff -= 2*math.pi
            ang_mid_l = ang_start_l + diff/2.0
            
            pt_mid_arc_l = adsk.core.Point3D.create(
                center_pt.x + r_root*math.cos(ang_mid_l), 
                center_pt.y + r_root*math.sin(ang_mid_l), 0)
            
            arc_root_l = arcs.addByThreePoints(leg_l_end, pt_mid_arc_l, curr_root_mid_l)

            ang_start_r = math.atan2(leg_r_end.geometry.y - center_pt.y, leg_r_end.geometry.x - center_pt.x)
            ang_end_r = math.atan2(curr_root_mid_r.y - center_pt.y, curr_root_mid_r.x - center_pt.x)
            
            diff = ang_end_r - ang_start_r
            while diff <= -math.pi: diff += 2*math.pi
            while diff > math.pi: diff -= 2*math.pi
            ang_mid_r = ang_start_r + diff/2.0
            
            pt_mid_arc_r = adsk.core.Point3D.create(
                center_pt.x + r_root*math.cos(ang_mid_r), 
                center_pt.y + r_root*math.sin(ang_mid_r), 0)
            
            arc_root_r = arcs.addByThreePoints(leg_r_end, pt_mid_arc_r, curr_root_mid_r)

            # 6. 齿根倒角 (Root Fillet)
            if root_fillet_r > 0.001:
                try:
                    arcs.addFillet(obj_for_fillet_l, leg_l_end.geometry, arc_root_l, leg_l_end.geometry, root_fillet_r)
                except: pass 

                try:
                    arcs.addFillet(obj_for_fillet_r, leg_r_end.geometry, arc_root_r, leg_r_end.geometry, root_fillet_r)
                except: pass

        sketch.isComputeDeferred = False