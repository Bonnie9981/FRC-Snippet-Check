# Up-to-date example
```java
import edu.wpi.first.math.geometry.Pose2d;
import edu.wpi.first.wpilibj.TimedRobot;
import edu.wpi.first.wpilibj.motorcontrol.PWMSparkMax;
import edu.wpi.first.wpilibj2.command.Command;
import edu.wpi.first.wpilibj2.command.Commands;

m_controller.a().onTrue(Commands.runOnce(() -> m_arm.raise(), m_arm));
m_controller.b().whileTrue(m_intake.run(() -> m_intake.spin()));
```
