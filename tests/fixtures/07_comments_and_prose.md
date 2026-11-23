In 2023 `whenPressed` was replaced by `onTrue`. SpeedControllerGroup is gone too.
```java
// Old: m_button.whenPressed(new RaiseArm());
/* SpeedControllerGroup was removed */
 * see RobotDrive docs
m_button.onTrue(new RaiseArm());
```
