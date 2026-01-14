from manim import *
import numpy as np

class GenScene(Scene):
    def construct(self):
        # 1) Create the Sun
        sun = Dot(radius=0.4, color=YELLOW)
        
        # 2) Create the Earth
        earth = Dot(radius=0.15, color=BLUE)
        
        # 3) Create the Moon
        moon = Dot(radius=0.08, color=GREY)

        # Add bodies to the scene
        self.add(sun, earth, moon)

        # Tracker to control the movement (angle in radians)
        # This acts as our "time" variable
        angle = ValueTracker(0)

        # Updater for Earth: Moves in a circle of radius 3 around the center
        earth.add_updater(lambda m: m.move_to(
            RIGHT * 3 * np.cos(angle.get_value()) +
            UP * 3 * np.sin(angle.get_value())
        ))

        # Updater for Moon: Moves in a circle of radius 0.8 around the Earth
        # Multiplier 12 makes the moon orbit faster than the Earth (approx 12 months/year)
        moon.add_updater(lambda m: m.move_to(
            earth.get_center() +
            RIGHT * 0.8 * np.cos(12 * angle.get_value()) +
            UP * 0.8 * np.sin(12 * angle.get_value())
        ))

        # 4) Create trails (orbits)
        # TracedPath automatically draws a line following the object's center
        earth_trail = TracedPath(earth.get_center, stroke_color=BLUE_E, stroke_width=2)
        moon_trail = TracedPath(moon.get_center, stroke_color=WHITE, stroke_width=1)
        
        self.add(earth_trail, moon_trail)

        # 5) Run the animation
        # Rotate 2*PI (360 degrees) over 10 seconds with linear speed
        self.play(
            angle.animate.set_value(2 * PI),
            run_time=10,
            rate_func=linear
        )
        
        self.wait(1)